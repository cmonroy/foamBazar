import os
from ofCase import OfCase
from inputFiles import FvSchemes, FvSolution, ControlDict, DecomposeParDict, TransportProperties, TurbulenceProperties, RASProperties
from inputFiles import BoundaryPressure, BoundaryVelocity, BoundaryPointDisplacement, BoundaryAlpha
from inputFiles import RelaxZone, noWaves, WaveProperties, DynamicMeshDict
import shutil
from meshTools import getBounds


class SeakeepingCase(OfCase):

    handledFiles = OfCase.handledFiles
    additionalFiles = {}
    additionalFiles["boundaryPressure"] = ("0/org/p_rgh", BoundaryPressure)
    additionalFiles["boundaryVelocity"] = ("0/org/U", BoundaryVelocity)
    additionalFiles["boundaryPointDisplacement"] = ("0/org/pointDisplacement", BoundaryPointDisplacement)
    additionalFiles["boundaryAlpha"] = ("0/org/alpha.water", BoundaryAlpha)
    handledFiles = {**handledFiles, **additionalFiles}

    def __init__(self, *args, **kwargs):
        """
        Same arguments as OfCase + some boundary input files
        """

        for fattr in self.additionalFiles.keys():
            if fattr in kwargs.keys():
                setattr(self, fattr,  kwargs.pop(fattr))

        OfCase.__init__(self, *args, **kwargs)
        self.bounds = getBounds(os.path.join(self.meshFolder, "polyMesh/points.gz"))

    @classmethod
    def BuildFromParams(cls, case, mass, inertia, cog,
                        deltaT,
                        endTime,
                        speed,
                        wave,
                        inletRelax,
                        outletRelax,
                        sideRelax,
                        outletRelaxTarget,
                        meshMotion="cpMorphing",
                        innerDistance=None,
                        outerDistance=None,
                        adjustTimeStep=None,  # None for constant time step, [maxCo, maxAlphaCo, maxDeltaT] otherwise
                        nProcs=1,
                        OFversion=5,
                        *args, **kwargs):
        """Construct seakeeping case
        """

        # ControlDict
        pm = {}
        pm["mass"] = mass
        pm["cog"] = cog
        pm["inertia"] = inertia
        pm["speed"] = speed

        res = cls(case=case, **kwargs)
        res.nProcs = nProcs
        res.wave = wave
        res.speed = speed
        res.controlDict = ControlDict.Build(case, deltaT=deltaT, adjustTimeStep=adjustTimeStep, endTime=endTime)
        res.decomposeParDict = DecomposeParDict.Build(case, nProcs=res.nProcs, version=OFversion)
        res.setBoundaries()
        res.setDefaultSchemeAndSolution()

        #----------- Set waves
        res.inletRelax = RelaxZone(name="inlet", relax=True, waveCondition=res.wave, origin=[res.bounds[0][1], 0, 0], orientation=[-1, 0, 0], length=inletRelax)
        res.sideRelax = RelaxZone(name="side", relax=True, waveCondition=res.wave, origin=[0, res.bounds[1][1], 0], orientation=[0, -1, 0], length=sideRelax)

        if outletRelaxTarget == "still":
            res.outletRelax = RelaxZone(name="outlet", relax=True, waveCondition=noWaves, origin=[res.bounds[0][0], 0, 0], orientation=[1, 0, 0], length=outletRelax)
        elif outletRelaxTarget == "incident":
            res.outletRelax = RelaxZone(name="outlet", relax=True, waveCondition=res.wave, origin=[res.bounds[0][0], 0, 0], orientation=[1, 0, 0], length=outletRelax)
        else:
            raise(Exception('"still" of "incident" expected for outletRelaxTarget'))

        res.waveProperties = WaveProperties.Build(res.case, res.wave, relaxZones=(res.inletRelax, res.outletRelax, res.sideRelax))

        #----------- Set mechanics
        res.dynamicMeshDict = DynamicMeshDict.Build_free(res.case, mass=mass, cog=cog, inertia=inertia,
                                                         rampTime=0.1, releaseTime=0.0,
                                                         hullPatch="(ship)", meshMotion=meshMotion, innerDistance=innerDistance, outerDistance=outerDistance)

        return res

    def __str__(self):

        s = OfCase.__str__(self)
        return "SeakeepingCase : " + s

    def setDefaultSchemeAndSolution(self, overwrite=False):
        if self.fvSchemes == None or overwrite:
            self.fvSchemes = FvSchemes.Build(self.case, orthogonalCorrection="implicit", limitedGrad=False, simType="tds")
        if self.fvSolution == None or overwrite:
            self.fvSolution = FvSolution.Build(self.case)
        if self.transportProperties == None or overwrite:
            self.transportProperties = TransportProperties.Build(self.case)

    def setBoundaries(self):
        """Prepare boundaries input files
        """
        self.boundaryPressure = BoundaryPressure.Build(self.case, self.symmetry)
        self.boundaryVelocity = BoundaryVelocity.Build(self.case, speed=self.speed, symmetry=self.symmetry, relaxZone=True)
        self.boundaryPointDisplacement = BoundaryPointDisplacement.Build(self.case, self.symmetry)
        self.boundaryAlpha = BoundaryAlpha.Build(self.case, self.symmetry)

    def writeAllinit(self, batchName="Allinit"):
        """To be implemented in subclass"""

        template = """set -x
(
    cp 0/org/{alpha.water,U,p_rgh,pointDisplacement} 0/
    setSet -batch blendingZone.batch
    setsToZones
    initWaveField
) 2>&1 | tee init.log
"""

        template2 = """(
    decomposePar -cellDist
    mpirun -np {:} initWaveField -parallel
)  2>&1 | tee init_parellel.log
"""

        with open(os.path.join(self.case, "Allinit"), "w") as f:
            f.write(template)
            if self.nProcs > 1:
                f.write(template2.format(self.nProcs))

    def writeRun(self):
        """To be implemented in subclass"""
        with open(os.path.join(self.case, "Allrun"), "w") as f:
            if self.nProcs > 1:
                f.write("mpirun -n {} foamStar -parallel 2>&1 | tee foamStar.log".format(self.nProcs))
            else:
                f.write("foamStar 2>&1 | tee foamStar.log")

    def runInit(self):
        import subprocess
        print("Run initialization")
        os.chdir(self.case)
        subprocess.call(["/bin/bash", "Allinit"], shell=False)

    def run(self):
        import subprocess
        print("Run initialization")
        os.chdir(self.case)
        subprocess.call(["/bin/bash", "Allrun"], shell=False)

    def writeFiles(self):

        print("Writting input file")
        OfCase.writeFiles(self)
        self.boundaryPressure.writeFile()
        self.boundaryVelocity.writeFile()
        self.boundaryPointDisplacement.writeFile()
        self.boundaryAlpha.writeFile()

        # Copy mesh
        print("Copying mesh")
        if not os.path.exists(os.path.join(self.constfolder_, "polyMesh")):
            shutil.copytree(os.path.join(self.meshFolder, "polyMesh"), os.path.join(self.constfolder_, "polyMesh"))