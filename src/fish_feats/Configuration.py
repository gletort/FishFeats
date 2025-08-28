import os
from magicgui.widgets import TextEdit
from napari.utils.notifications import show_info
import ast
import csv
import configparser

class Configuration:

    def __init__(self, filename, show=True):
        self.filename = filename
        self.parameters = configparser.ConfigParser()
        if self.has_config():
            self.read_parameterfile()
        self.blabla = TextEdit()
        self.blabla.read_only = True
        self.blabla.name = "Blabla"
        self.blabla.value = "Fish&Feats on file "+filename
        if show:
            self.blabla.show()
        self.blablasaved = self.blabla.value
     
    def has_config(self):
        self.hascfg = os.path.exists(self.filename)
        return self.hascfg

    def read_parameterfile(self):
        """ Read the .cfg file that contains the parameters as dict """
        self.parameters.read(self.filename)

    def write_parameterfile(self):
        """ Save the .cfg file that contains the parameters as dict """
        with open(self.filename, "w") as cfgfile:
            self.parameters.write(cfgfile)

    def read_scale(self, mig):
        """ Read the parameters relative to image scalings and load the values """
        if "ImageScalings" in self.parameters:
            paras = self.parameters["ImageScalings"]
            if "scalexy" in paras:
                mig.scaleXY = float(paras["scalexy"])
            if "scaleZ" in paras:
                mig.scaleZ = float(paras["scalez"])
            if "direction" in paras:
                mig.zdirection = 1
                if paras["direction"].find("top high z") >= 0:
                    mig.zdirection = -1
            var = "junction_channel"
            if var in paras:
                if paras[var] == "None":
                    mig.junchan = None
                else:
                    mig.junchan = int(paras[var])
            var = "nuclei_channel"
            if var in paras:
                if paras[var] == "None":
                    mig.nucchan = None
                else:
                    mig.nucchan = int(paras[var])

    def read_junctions(self):
        """ returns the parameters for junction segmentation """
        if "JunctionSeg" in self.parameters:
            paras = self.parameters["JunctionSeg"]
            return paras
        return None 

    def read_parameter_set(self, name):
        """ returns the set of parameters """
        if name in self.parameters:
            return self.parameters[name]
        return None


    def setText(self, text):
        self.blabla.value = text
    
    def addText(self, text):
        self.blabla.value += "\n"+text
    
    def addTmpText(self, text):
        self.blablasaved = self.blabla.value
        self.addText(text)

    def removeTmpText(self):
        self.blabla.value = self.blablasaved

    def addSectionText(self, text):
        self.blabla.value += "\n\n********************************************\n##"+text+"\n"

    def addGroupParameter(self, name):
        """ Add a set of parameter """
        if name not in self.parameters:
            self.parameters[name] = {} 

    def addParameter(self, paratype, paraname, paravalue):
        """ Add one parameter to the set of parameters """
        if paravalue is None:
            (self.parameters[paratype])[paraname] = "None"
        else:
            (self.parameters[paratype])[paraname] = str(paravalue)

    def addTextParameter(self, cat, paraname, paravalue):
        self.blabla.value += "\n%"+cat+"->"+paraname+" = "+str(paravalue)
    
    def saveText(self):
        with open(self.filename, 'w') as f:
            f.write(self.blabla.value)
        show_info("Informations saved in file "+self.filename+"")
