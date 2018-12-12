
import os
import shutil
import subprocess

from inputFiles.gravity import Gravity
from inputFiles import ControlDict, FvSchemes, FvSolution, DecomposeParDict, DynamicMeshDict,  TransportProperties, WaveProperties
from inputFiles.turbulenceProperties import TurbulenceProperties, RASProperties
from fsTools import getFoamTimeFolders


#Always written
                    

class OfCase(object):
    """ Base class for openFoam case
    Can be sub-classed to deal with more specific situation (example : DropTestCase, SeakeepingCase)
    """
    
    handledFiles =   [
                    "controlDict",
                    "decomposeParDict",

                    "fvSchemes",
                    "fvSolution",
                    "dynamicMeshDict",
                    "transportProperties",
                    "waveProperties",
                      ]
                    #Always written
                    #"rasProperties"        : ("constant/RASProperties", RASProperties),
                    #"turbulenceProperties" : ("constant/turbulenceProperties", TurbulenceProperties),
                    #"gravity" : ("constant/gravity", Gravity),
                    
                 

    def __init__(self, case, nProcs=1, controlDict=None,
                                       fvSchemes=None,
                                       fvSolution=None,
                                       waveProperties=None,
                                       dynamicMeshDict=None,
                                       transportProperties=None,
                                       decomposeParDict=None,
                                       turbulenceModel = "laminar",
                                       symmetry = False,
                                       gravity = 9.81,
                                       OFversion = 5,         #OpenFoam version
                                       solver = "foamStar",   #Solver name (foamStar, navalFoam)
                                       isMesher = False,
                                       clean = False,  #True => Remove case folder and go on. #False: ask user interactively
                                       meshFolder = None ,
                                       ) :


        self.case = os.path.abspath(case)  # path to case
        
        self.clean(clean)
        
        self.nProcs = nProcs

        #system
        self.controlDict = controlDict
        self.fvSchemes = fvSchemes
        self.fvSolution = fvSolution
        self.decomposeParDict = decomposeParDict
        
        #constant
        self.waveProperties = waveProperties
        self.dynamicMeshDict = dynamicMeshDict
        self.transportProperties = transportProperties
        self.turbulenceModel = turbulenceModel
        self.turbulenceProperties = TurbulenceProperties.Build(case , turbulenceModel )
        self.RASProperties = RASProperties.Build(case , turbulenceModel )
        

        self.meshFolder = meshFolder

        self.symmetry = symmetry
        self.gravity = gravity
        self.OFversion = OFversion
        self.solver = solver
        self.isMesher = isMesher
        
        self.sysfolder_ = os.path.join(self.case,"system")
        self.zerofolder_ = os.path.join(self.case,"0")
        self.orgfolder_ = os.path.join(self.case,"0","org")
        self.constfolder_ = os.path.join(self.case,"constant")
        
        self.writeFolders()


    def writeFolders(self) :
        print('Create file tree')
        if not os.path.exists(self.sysfolder_): os.makedirs(self.sysfolder_)
        if not os.path.exists( os.path.join(self.zerofolder_, "org")): os.makedirs( os.path.join(self.zerofolder_, "org"))
        if not os.path.exists( self.zerofolder_): os.makedirs( self.zerofolder_)
        if not os.path.exists( self.constfolder_): os.makedirs( self.constfolder_)

        if self.isMesher:
            self.polyfolder_ = os.path.join(self.case,"constant","polyMesh")
            self.trifolder_ = os.path.join(self.case,"constant","triSurface")
            if not os.path.exists( self.polyfolder_): os.makedirs( self.polyfolder_)
            if not os.path.exists( self.trifolder_): os.makedirs( self.trifolder_)

        self.createParaviewFile()


    def clean(self,clean = False) :
        if os.path.exists(self.case):
            if clean:
                print('Overwriting case "{}"'.format(self.case))
                shutil.rmtree(self.case)
            else:
                valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
                res = input('Case "{}" already exists, do you want to overwrite ? (y/n) '.format(self.case)).lower()
                if valid.get(res,False):
                    shutil.rmtree(self.case)
                else:
                    print('Exiting')
                    os._exit(1)


    @classmethod
    def Read( cls, case, source, solver = "foamStar" ):
        """Read file from existing folder
        """
        source = os.path.abspath(source)
        case = os.path.abspath(case)
        fileDict = {}
        for f in cls.handledFiles:
            fname =  os.path.join(source, path )
            if os.path.exists(fname) :
                tmpobj = getFileClass()( os.path.join(source, getFilePath(f) ) , read = True)
                tmpobj.case = case
                tmpobj.name = tmpobj.name.replace(source, case)
                fileDict[ f ] = tmpobj
            else: 
                print (fname, "does not exists")
        return cls( case, **fileDict , solver = solver, meshFolder = os.path.join(source, "constant") )


    def createParaviewFile(self):
        #create file for Paraview
        open(os.path.join(self.case,'view.foam'), 'a').close()

    @classmethod
    def BuildFromAllParameters(cls, case, isMesher=False):
        return OfCase(case, isMesher)


    def writeFiles(self) :
        """Write all input file in case folder
        """

        gravity = Gravity( case = self.case, g = self.gravity )
        gravity.writeFile()

        self.controlDict.writeFile()
        self.fvSchemes.writeFile()
        self.fvSolution.writeFile()
        self.decomposeParDict.writeFile()
        
        if self.turbulenceProperties is not None:       self.turbulenceProperties.writeFile()
        if self.RASProperties is not None:              self.RASProperties.writeFile()
        if self.transportProperties is not None:        self.transportProperties.writeFile()
        if self.dynamicMeshDict is not None:            self.dynamicMeshDict.writeFile()
        if self.waveProperties is not None:             self.waveProperties.writeFile()
        
        #write Allinit and Allclean scripts
        if not os.path.exists( "Allclean" ): self.writeAllclean()
        if not os.path.exists( "Allinit" ): self.writeAllinit()

    def runInit(self) :
        #run Allclean and Allinit script
        p = subprocess.Popen(['./Allclean'], cwd=self.case)
        p.wait()

        p = subprocess.Popen(['./Allinit'], cwd=self.case)
        p.wait()

    def run(self) :
        #run Allrun script
        if not os.path.exists( "run" ):
            self.writeRun()
        p = subprocess.Popen(['./run'], cwd=self.case)
        p.wait()

    def writeAllinit(self):
        """To be implemented in subclass"""
        raise(NotImplementedError)

    def writeRun(self):
        """To be implemented in subclass"""
        raise(NotImplementedError)

    def Allclean(self):
        """To be implemented in subclass"""
        raise(NotImplementedError)

    def copyMesh(self, meshDir, meshTime, overwrite=False):
        if meshTime=='latestTime':
            timeFolders = getFoamTimeFolders(meshDir)
            meshTimeFolder = timeFolders[-1]
        elif meshTime=='constant':
            meshTimeFolder = 'constant'
        else:
            meshTimeFolder = meshTime

        print('Copy mesh from folder ' + meshTimeFolder)

        shutil.copytree( os.path.join( meshDir , meshTimeFolder ,'polyMesh') , os.path.join( self.case , "constant/polyMesh"))
        shutil.copytree( os.path.join( meshDir , "constant" ,'triSurface') , os.path.join( self.case  , "constant/triSurface"))

    def runSbatch(self):
        self.writeSbatch()
        subprocess.call(['sbatch', 'run.sh'], cwd=self.case)
