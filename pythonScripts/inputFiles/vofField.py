from inputFiles.ofDictionary import ofDictionary, bcDictionary
from PyFoam.Basics.DataStructures import Dimension, Vector

"""
  Convenience class to simply write "g"
"""
class vofField(bcDictionary) :
    """
    Gravity dictionnary
    """
    def __init__(self , root, fdir, fid="alpha.water", **kwargs):
        bcDictionary.__init__(self , root,fdir,fid,**kwargs)
        if self.exists: return
        self.header['class']='volScalarField'
        # update according to user input
        self.update(**kwargs)

if __name__ == "__main__" : 
   print(vofField("test"))



