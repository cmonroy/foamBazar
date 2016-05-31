#!/usr/bin/python
"""
   Plot force output from Foam Star
"""

try :
   from TimeDomain import TimeSignals as ts
except ImportError as  e:
   print "Can not load TimeSignals, please add 'shared-code/Python' (from repo http://svn-drsvn.eua.bvcorp.corp/dr/shared-code) to your PYTHON_PATH\n"
   raise Exception(e)


if __name__ == "__main__" :

   """
      Example of use :

      FoamStarFourier forces.dat                          #->plot all the forces components
      FoamStarFourier forces.dat -indexName Fx Fy         #->plot the selected components, based on labels
      FoamStarFourier forces.dat -index     0  1          #->plot the selected components, based on indexes

   """
   import argparse
   parser = argparse.ArgumentParser(description='FoamStar forces plot')
   parser.add_argument( "forceFile" )
   parser.add_argument('-indexName',  nargs='+', type = str , help='Index to plot' )
   parser.add_argument('-index',  nargs='+', type = int , help='Index to plot' )
   args = parser.parse_args()

   a = ts.read( args.forceFile , reader = "openFoamReader" , field = "total") 

   slFFT= ts.slidingFFT( a, 1.8)

   if args.indexName :
      slFFT.plotTS( [a.columnTitles.index( s ) for s in args.indexName] )
   elif args.index :
      slFFT.plotTS( args.index )
   else:
      slFFT.plotTS( "all" )
