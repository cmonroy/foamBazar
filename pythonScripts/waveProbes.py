"""
   Prepare input for wave probes
"""

from compatOF import surfaceElevation, alpha
from PyFoam.RunDictionary.ParsedParameterFile import WriteParameterFile


def setWaveProbes( waveProbesList , version = "foamStar" , writeProbesInterval = 0.1 ) :

   d = { surfaceElevation[version] : { "type" : "surfaceElevation" ,
                                      "outputControl" : "timeStep" ,
                                      "outputInterval" : 10,
                                      "interpolationScheme" : "cellPointFace"
                                 }

           }
   if version != "foamStar" :
      d[surfaceElevation[version]]["file"] =   "surfaceElevation.dat"
      d[surfaceElevation[version]]["fields"] = alpha[version]
      if writeProbesInterval is not None :
         d[surfaceElevation[version]]["surfaceSampleDeltaT"] =  writeProbesInterval
   d[surfaceElevation[version]]["sets"] =   [ "p_{0:05} {{start ({1:} {2:} {3:}); end ({1:} {2:} {4:});  type face; axis z; nPoints {5:}; }}".format( i ,  *p )  for i, p  in enumerate(waveProbesList)  ]

   return d


def createLinearWaveProbesList( xMin, xMax, nX, y, zMin, Zmax, nZ) :
	waveProbesList = []
	deltaX=(xMax-xMin)/(nX-1)
	for i in range(0,nX):
		waveProbesList.append([xMin+i*deltaX, y, zMin, Zmax, nZ])
	return waveProbesList

if __name__ == "__main__" :

   # works with tuples or with lists
   #waveProbesList = ( (10.,0.,-1.,+1 , 100) , (15.,0.,-1.,+1 , 100) )
   waveProbesList = [ [10.,0.,-1.,+1 , 100] , [15.,0.,-1.,+1 , 100] ]
   print waveProbesList

   waveProbesList=createLinearWaveProbesList( -100.0, 100.0, 201, 0.05, -3.0, 3.0, 100)
   print waveProbesList
   d = setWaveProbes ( waveProbesList, "foamStar" , writeProbesInterval = 0.01 )

   waveProbFile = WriteParameterFile("waveProb.inc")
   waveProbFile["functions"] = d
   waveProbFile.writeFile()


