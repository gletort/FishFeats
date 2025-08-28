from math import floor, sqrt, pow, pi, ceil, atan2, cos, sin
import numpy as np
from skimage.measure import regionprops
from skimage.segmentation import find_boundaries, expand_labels
from scipy.ndimage.morphology import distance_transform_edt
from skimage.morphology import convex_hull_image
from fish_feats.Association import associate_nucleiToCell
import skimage.metrics as imetrics
import fish_feats.Utils as ut

class Cell:
    """ Handle the cell: label of the cell, position of the center.."""
    
    def __init__(self, label=-1, area=-1, center=None, bbox=None):
        self.label = int(label)  ## ensure that it is an integer
        self.bbox = bbox
        self.centerXY = center
        self.area = area
        self.zjunc = -99999    ## z position of junction
        self.counter = {} ## to count something
        self.direction = 0  ## if nucleus is above or bellow junction
        self.projAnglePoints = None   ## contour points by angle
        self.measures = {}  ## save measures of the cell
        self.features = {}
   
    def juncCenter(self):
       return (self.zjunc, self.centerXY[0], self.centerXY[1])

    def hasZpos( self ):
        """ Check if the cell has a z position """
        return self.zjunc != -99999

    def setZJunction( self, zpos ):
        self.zjunc = zpos
        if "ZPosPixel" in self.measures.keys():
            if self.measures["ZPosPixel"] is not None:
                self.measures["ZPosPixel"] = zpos
    
    def updateZJunction( self, zpos, scaleZ ):
        self.zjunc = zpos
        if "ZPosPixel" in self.measures.keys():
            if self.measures["ZPosPixel"] is not None:
                self.measures["ZPosPixel"] = zpos
            if self.measures["ZPosMicron"] is not None:
                self.measures["ZPosMicron"] = zpos * scaleZ

    def getRadius( self ):
        """ Return the mean cell radius """
        return sqrt( self.area/pi )
                
    def get_maskBB( self, img ):
        """ Get the cell mask from img, cropped by the bounding box """
        cropimg = img[self.bbox[0]:self.bbox[2], self.bbox[1]:self.bbox[3]]
        cellmask = (cropimg==self.label)
        return cellmask, self.bbox

    def fillFeature( self, img, featname, featimg, value ):
        """ Fill the feature and feature image with the value """
        cellmask, bbox = self.get_maskBB( img )
        self.putFeature( featname, value )
        featimg[bbox[0]:bbox[2],bbox[1]:bbox[3]][cellmask] = value
        return featimg

    def calcProjContour( self, dang, mask ):
        """ calculate the projection (union) of the contours by angle """
        ang = 0
        ct = (self.centerXY[0], self.centerXY[1])
        listPoints = []
        while ang < 360:
            dis = 0.001
            dis = self.getRadius()*0.3 ## less than half the cell mean radius, very likely inside 
            point = (ct[0]+dis*cos(ang/180.0*pi), ct[1]+dis*sin(ang/180.0*pi))
            while mask[int(point[0]), int(point[1])] > 0:
                dis += 0.2
                point = (ct[0]+dis*cos(ang/180.0*pi), ct[1]+dis*sin(ang/180.0*pi))
                ## check if don't leave the image
                if (int(point[0]) < 0) or (int(point[0])>=mask.shape[0]):
                    break
                if (int(point[1]) < 0) or (int(point[1])>=mask.shape[1]):
                    break
            ang += dang
            listPoints.append( (int(point[0]), int(point[1])) ) ## put in order
        self.projAnglePoints = listPoints

    def verticalDistance( self, pt, scaleZ=1 ):
        """ Distance in Z """
        return abs( pt[0] - self.zjunc )*scaleZ

    def mean_radius( self ):
        """ Mean cell radius (in pixels) """
        return sqrt( self.area/pi )

    def setZJunctions( self, img ):
        """ find best z (with higher intensity in the object) """
        self.zjunc = 0
        #if np.sum(mask) > 0:
        boximg = img[:, self.bbox[0]:self.bbox[2], self.bbox[1]:self.bbox[3]]
        #boximg = np.where( mask, boximg, np.zeros(boximg.shape) )
        maskedimg = np.mean( boximg, axis=(1,2) )
        self.setZJunction( np.argmax(maskedimg) )
    
    def setZJunctionsFromList(self, zlist):
        """ Define the z of the cell from the list of cell label and pos """
        self.zjunc = 0
        ind = -1
        if self.label in zlist["CellLabel"]: 
            ind = (zlist["CellLabel"]).index(self.label)
        if ind >= 0:
            self.zjunc = zlist["ZPos"][ind]
            return 1
        return 0

    def setZJunctionsFromMap(self, zmap):
        """ Define the z of the cell from the zmap """
        self.zjunc = 0
        bbmap = zmap[self.bbox[0]:self.bbox[2], self.bbox[1]:self.bbox[3]]
        zjunc = floor(np.median(bbmap))
        self.setZJunction( zjunc )
    
    def findZJunctions(self, img, proj):
        """ find best z (higher correlation in the object) """
        self.zjunc = 0
        if self.bbox is not None:
            bb = np.copy(self.bbox)
            for i in range(2):
                bb[i] = bb[i]*0.8
                if bb[i] < 0:
                    bb[i] = 0
                bb[i+2] = bb[i+2]*1.2
                if bb[i+2] > proj.shape[i]:
                    bb[i+2] = proj.shape[i]
            boximg = img[:, bb[0]:bb[2], bb[1]:bb[3]]
            boxproj = proj[bb[0]:bb[2], bb[1]:bb[3]]
            self.find_max_correlation(boximg, boxproj)

    def find_max_correlation(self, img3d, proj):
        """ Find z at which img3d and proj are the closest """
        best_score = 0
        for z, zslice in enumerate(img3d):
            score = imetrics.normalized_mutual_information(zslice, proj) 
            if best_score < score:
                best_score = score
                self.zjunc = z

    
    def setDirection(self, dirsign=-1):
        """ direction where above/below the cell is: if dirsign<0, increasing z means going below """
        self.direction = dirsign 
    
    def distance3D2center(self, pt, scaleXY, scaleZ):
        return sqrt( pow(self.zjunc-pt[0],2)*scaleZ*scaleZ + pow(self.centerXY[0]-pt[1],2)*scaleXY*scaleXY + pow(self.centerXY[1]-pt[2],2)*scaleXY*scaleXY )

    def distance2center(self, pt):
        return sqrt( pow(self.centerXY[0]-pt[0],2) + pow(self.centerXY[1]-pt[1],2) )
    
    def resetMeasures(self):
        self.measures = {}
    
    def resetFeatures(self):
        self.features = {}
    
    def resetMeasure(self, name):
        if self.measures.get(name) is not None:
            self.measures[name] = None
    
    def resetFeature(self, name):
        if self.features.get(name) is not None:
            self.features[name] = None
    
    def putMeasure(self, name, val=0):
        self.measures[name] = val
    
    def putFeature(self, name, val=0):
        self.features[name] = val
    
    def getMeasure(self, name):
        """ Get the value of the measure for the cell"""
        return float(self.measures.get(name))
    
    def getFeature(self, name):
        """ The feature value of a cell is an integer (a class)"""
        if self.features.get(name) is None:
            return 0
        if self.features[name] == "":
            return 0
        return int(self.features.get(name))
    
    def getMeasures(self):
        return self.measures
    
    def getFeatures(self):
        return self.features

    def loadResults( self, results ):
        """ Load previous results from a dict """
        for key, val in results.items():
            if key.startswith("Feat_"):
                if self.features.get(key) is None:
                    if (val is None) or (val==""):
                        ## missing value
                        #self.features[key] = -99999
                        continue
                    else:
                        self.features[key] = int( float(val) )
                    continue
            if key.startswith("nbRNA_C"):
                if self.counter.get(key) is None:
                    if (val is None) or (val==""):
                        ## missing value
                        self.counter[key] = -99999
                    else:
                        self.counter[key] = int( float(val) )
                    continue
            if self.measures.get(key) is None:
                if key in ["CellId", "CellLabel", "NucleusLabel", "NucleusId"]:
                    if (val is None) or (val==""):
                        ## missing value
                        self.measures[key] = -99999
                    else:
                        self.measures[key] = int( float(val) )
                else:
                    if (val is None) or (val==""):
                        ## missing value
                        #self.measures[key] = -99999
                        continue
                    else:
                        self.measures[key] = float(val)
                if key == "ZPosPixel":
                    if (val is None) or (val==""):
                        self.zjunc = -99999
                    else:
                        self.zjunc = int( float(val) )


    def addMeasures( self, measures ):
        """ Add previous measures to the cell """
        for key, val in measures.items():
            #if self.measures.get(key) is None:
            self.measures[key] = val
            if key == "ZPosPixel":
                self.zjunc = int( float(val) )

    def remove_measures( self, name, start=True ):
        """ Remove measures of given name or starting with name """
        for meas in self.measures.keys():
            if meas == name:
                del self.measures[meas]
                continue
            if start:
                if meas.startswith( name ):
                    del self.measures[meas]

    def getMeasuresKeys(self):
        return self.measures.keys()
    
    def getFeaturesKeys(self):
        return self.features.keys()
    
    def resetCounts(self):
        self.counter = {}
    
    def resetCount(self, name, zero=False):
        if self.counter.get(name) is not None:
            self.counter[name] = 0 
        elif zero:
            self.counter[name] = 0

    def addCount(self, name, val=1):
        if self.counter.get(name) is None:
            self.counter[name] = val
        else:
            self.counter[name] += val
    
    def getCount(self, name):
        if self.counter.get(name) is None:
            return 0
        return self.counter[name]

    def getCounts( self ):
        """ Returns all RNA counts """
        return self.counter

    def addCountResults( self, rnachannels, methods ):
        """ Get the counts of the cell """
        for ir, rnac in enumerate(rnachannels):
            if type(methods) == list:
                cmethod = methods[ir]
            else:
                cmethod = methods
            self.measures[cmethod] = self.getCount(cmethod)

    
    def extremeZ( self, above=1 ):
        abz = self.zjunc
        if self.direction is not None:
            abz = self.zjunc - self.direction*above
        return abz
    
    def aboveCell(self, pt, dz=2):
        if dz is None or self.direction == 0:
            return False
        return (self.zjunc-pt[0])*(self.direction)>dz
    
    def belowApicalSurface(self, pt, dz=2):
        if self.direction == 0:
            return False
        diffz = (self.zjunc-pt[0]) * (-self.direction)
        return ( (diffz>0) and (diffz <= dz) )
    
    def insideBounds(self, boundbox):
        """ test if cell is within bounds """
        if self.bbox[0] < boundbox[0]:
            return False
        if self.bbox[1] < boundbox[1]:
            return False
        if self.bbox[2] > boundbox[2]:
            return False
        if self.bbox[3] > boundbox[3]:
            return False
        return True
    
    def insideBorderCenter(self, boundbox):
        """ test if cell center is within border """
        if self.centerXY[0] < boundbox[0]:
            return False
        if self.centerXY[1] < boundbox[1]:
            return False
        if self.centerXY[0] > boundbox[2]:
            return False
        if self.centerXY[1] > boundbox[3]:
            return False
        return True



    def angleContour(self, dang, imjun, bbox):
        """ Get the contour postion at each angle around the center """ 
        cent = [self.centerXY[0], self.centerXY[1]]
        cent[0] = cent[0]-bbox[1]
        cent[1] = cent[1]-bbox[2]
        rmean = sqrt(self.area)/pi
        ang = 0
        angPts = []
        while ang < 360:
            inside = True
            dis = rmean*0.5
            while inside:
                point = [int(cent[0]+dis*cos(ang/180.0*pi)), int(cent[1]+dis*sin(ang/180.0*pi))]
                ## be sure point doesn't leave the image (if on border)
                for i in range(2):
                    if point[i] < 0:
                        point[i] = 0
                        inside = False
                    if point[i] >= imjun.shape[i]:
                        point[i] = imjun.shape[i]-1
                        inside = False
                if inside:
                    inside = (imjun[point[0], point[1]] > 0)
                dis += 0.1
            angPts.append( point )
            ang += dang
        return angPts


    def insideBorderCenter(self, border):
        """ test if center is whithin border with a margin """
        if self.centerXY[0] < border[0]:
            return False
        if self.centerXY[0] > border[2]:
            return False
        if self.centerXY[1] < border[1]:
            return False
        if self.centerXY[1] > border[3]:
            return False
        return True
    
    def writeZ(self):
        """ Write z and label value """
        result = {}
        result["CellLabel"] = self.label
        result["ZPosPixel"] = self.zjunc
        return result

    def measureCell( self, cellind, scaleXY, scaleZ ):
        if self.measures is None:
            self.measures = {}
        if "CellId" not in self.measures:
            self.measures["CellId"] = cellind
            self.measures["CellLabel"] = self.label
            self.measures["XPosPixel"] = self.centerXY[1]
            self.measures["YPosPixel"] = self.centerXY[0]
            self.measures["ZPosPixel"] = self.zjunc
        if "XPosMicron" not in self.measures:
            self.measures["XPosMicron"] = self.centerXY[1]*scaleXY
            self.measures["YPosMicron"] = self.centerXY[0]*scaleXY
            self.measures["ZPosMicron"] = self.zjunc*scaleZ
            self.measures["CellAreaMicron2"] = self.area*scaleXY*scaleXY
    
    def measureOnlyCellLabel( self ):
        result = {}
        result["CellLabel"] = self.label
        return result

    def addMeasuresCytoplasmic( self, cellmask, cytoThickness, cytochannels, imagesCyto, meanbgints ):
        until = self.zjunc + self.direction*cytoThickness
        dep = min(self.zjunc, until)
        dep = max(dep, 0)
        end = max(self.zjunc, until)
        nz = imagesCyto[cytochannels[0]].shape[0]
        end = min(end, nz)
        for cyt, meanbgint in zip(cytochannels, meanbgints):
            intensities = imagesCyto[cyt][dep:end+1,cellmask]
            imean = np.mean(intensities)
            istd = np.std(intensities)
            imed = np.median(intensities)
            self.measures["Cyto"+str(cyt)+"_MeanIntensity"] = imean
            self.measures["Cyto"+str(cyt)+"_StdIntensity"] = istd 
            self.measures["Cyto"+str(cyt)+"_MedianIntensity"] = imed 
            self.measures["Cyto"+str(cyt)+"_MeanNormalisedIntensity"] = imean/meanbgint
            self.measures["Cyto"+str(cyt)+"_StdNormalisedIntensity"] = istd/meanbgint
            self.measures["Cyto"+str(cyt)+"_MedianNormalisedIntensity"] = imed/meanbgint
            self.measures["Cyto"+str(cyt)+"_SumIntensity"] = np.sum(intensities)
            self.measures["Cyto"+str(cyt)+"_SumNormalizedIntensity"] = np.sum(intensities/meanbgint)


class Nucleus:
    """ Label corresponding to imgnuc in pop """
    
    def __init__( self, label=-1, volume=-1, center=None, bbox=None ): 
        ### GAP in nucleus possible ?
        #cnts, inds = self.check_gap(cnts, inds)
        self.label = label
        self.volume = volume
        self.center = center
        self.zpos = center[0]
        self.bbox = bbox
        self.projAnglePoints = None   ## points of projected contour by angle
    
    def center2D(self):
        return (self.center[1], self.center[2])

    def zdistanceToCenter(self, zpt, scalez):
        return sqrt( pow(self.center[0]-zpt,2) )*scalez
    
    def distance2DToCenter(self, pt, scalexy):
        return sqrt( pow((self.center[1]-pt[0])*scalexy,2) + + pow((self.center[2]-pt[1])*scalexy,2) ) 

    
    def distanceToCenter(self, pt, scalexy, scalez):
        return sqrt( pow((self.center[0]-pt[0])*scalez,2) + pow((self.center[1]-pt[1])*scalexy,2) + + pow((self.center[2]-pt[2])*scalexy,2) ) 

    def updateLabel(self, imglab):
        cent = (int(self.center[0]), int(self.center[1]), int(self.center[2]))
        if imglab[cent] != self.cellind:
            if imglab[cent] <= 0:
                self.cellind = -1
            else:
                self.cellind = imglab[cent]

    def insideBorderCenter(self, border):
        """ test if center is whithin border """
        if self.center[1] < border[0]:
            return False
        if self.center[2] < border[1]:
            return False
        if self.center[1] > border[2]:
            return False
        if self.center[2] > border[3]:
            return False
        return True

    def insideBorder(self, border):
        """ test if nucleus is whithin border """
        if self.bbox[1] < border[0]:
            return False
        if self.bbox[2] < border[1]:
            return False
        if self.bbox[4] > border[2]:
            return False
        if self.bbox[5] > border[3]:
            return False
        return True

    def extremeZ( self, dlim, scaleZ ):
        return ( self.center[0]-dlim/scaleZ, self.center[0] + dlim/scaleZ )
    
    def calcProjContour( self, dang, imnuc, cell ):
        """ Get the contour along each angle """
        bbox = ut.mergeBoundingBox( cell.bbox, cell.zjunc, self.bbox )
        imnuc_crop = ut.cropBbox( imnuc, bbox )
        self.projAnglePoints = self.angleContour( dang, imnuc_crop, bbox )
    
    def getRadius( self ):
        """ Get mean nucleus radius """
        rmean = pow(self.volume*3.0/(4.0*pi),0.33)
        return rmean

    def angleContour(self, dang, imnuc, bbox):
        """ 
        Get the contour postion at each angle around the center 
        """ 
        cent = [self.center[1], self.center[2]]
        cent[0] = cent[0]-bbox[1]
        cent[1] = cent[1]-bbox[2]
        ang = 0
        angPts = []
        rmean = self.getRadius()
        nucshape = imnuc.shape[1:]
        img = np.max(imnuc, axis=0)
        img = convex_hull_image( img )
        inside = True
        while ang < 360:
            inside = True
            dis = rmean*0.4
            while inside:
                point = [int(cent[0]+dis*cos(ang/180.0*pi)), int(cent[1]+dis*sin(ang/180.0*pi))]
                ## be sure point doesn't leave the image (if on border)
                for i in range(2):
                    if point[i] < 0:
                        point[i] = 0
                        inside = False
                        break
                    if point[i] >= nucshape[i]:
                        point[i] = nucshape[i]-1
                        inside = False
                        break
                if inside:
                    inside = (img[int(point[0]), int(point[1])] > 0)
                dis += 0.1
            angPts.append( (int(point[0]+bbox[1]), int(point[1]+bbox[2])) )
            ang += dang
        return angPts

    def interpCenter(self, cent, z, ext=0):
        """ Get the interpolated distance between junction and nucelus - Or below the nucleus center if ext>0 """
        nuczpos = self.center[0]
        if ext > 0:
            nuczpos = nuczpos + (self.bbox[3]-nuczpos) * ext
        if nuczpos == cent[0]:
            if z == cent[0]:
                ratio = 0
            else:    ## both nuclei and junc same z
                return None, 0
        else:
            ratio = (z-cent[0])*1.0/(nuczpos - cent[0])
        if ratio < 0 or ratio>1:
            return None, ratio
        c1 = cent[1] + ratio*(self.center[1]-cent[1])
        c2 = cent[2] + ratio*(self.center[2]-cent[2])
        return (z, c1, c2), ratio
    
    def measureIntensity( self, mask, img, chan ):
        """ Measure the intensity inside the nucleus """
        intensities = img[mask]
        results = {}
        results["NucleusMeanIntensity_C"+str(chan)] = np.mean( intensities )
        results["NucleusStdIntensity_C"+str(chan)] = np.std( intensities )
        results["NucleusMedianIntensity_C"+str(chan)] = np.median( intensities )
        return results 

    def measureNuclear( self, nuclearchannels, image, meanbgints, result ):
        """ Measure intensity inside the nucleus """
        for nuc, meanbgint in zip(nuclearchannels, meanbgints):
            nucint = np.array([])
            for z, cnt in zip(self.zpos, self.contours):
                img = image[nuc,z,]
                intensities = getIntensities2D(cnt, img)
                nucint = np.concatenate((nucint, intensities))
                
            result.append(np.mean(nucint))
            result.append(np.std(nucint))
            result.append(np.median(nucint))
            result.append(np.mean(nucint/meanbgint))
            result.append(np.std(nucint/meanbgint))
            result.append(np.median(nuc/meanbgint))

    def getMeasures( self, scaleXY, scaleZ ):
        """ Return the measures of the nucleus """
        result = {}
        result["NucleusLabel"] = self.label
        result["NucleusVolumeInMicron3"] = self.volume * scaleXY*scaleXY*scaleZ
        result["NucleusZPositionInMicron"] = self.center[0]*scaleZ
        result["NucleusZPositionInPixels"] = self.center[0]
        result["NucleusXPosInPixels"] = self.center[2]
        result["NucleusYPosInPixels"] = self.center[1]
        return result
    

class Population:
    """ Ensemble of cells and nuclei """    
    def __init__(self, imageshape):
        self.cells = {}
        self.maxcell = 1
        self.nuclei = {}
        self.maxnucleus = 1
        self.association = {}
        self.imshape = imageshape
        self.imgcell = None
        self.imgnuc = None
        self.hullinited = 0

    def has_nuclei( self ):
        """ Returns if has segmented nuclei information """
        return ( (self.nuclei is not None) and (self.nuclei != {}) and ( len(self.nuclei) > 0 ) )

    def setCellImage(self, imgjun):
        self.imgcell = imgjun

    def setNucleiImage(self, imnuc):
        self.imgnuc = imnuc

    def addCell(self, cell):
        self.maxcell += 1
        self.cells[self.maxcell] = cell
    
    def addLabeledCell(self, cell, label):
        self.cells[label] = cell
        self.maxcell = max(self.maxcell, label)

    def addNucleus(self, nucleus): 
        self.maxnucleus += 1 
        self.nuclei[self.maxnuclei] = nucleus
    
    def addLabeledNucleus(self, nucleus, label, associate=False, scaleXY=1, scaleZ=1 ):
        self.nuclei[label] = nucleus
        self.maxnucleus = max(self.maxnucleus, label)
        if associate and self.cells.get(label) is not None:
            cellid = self.getCellId(label)
            self.associateNucleusWithCell( label, cellid, scaleXY, scaleZ )

    def getCellId(self, lab):
        cell = self.cells.get(lab)
        if cell is not None and cell.label==lab:
            return lab
        for cellid, cell in self.cells.items():
            if cell.label == lab:
                return cellid
        return -1
    
    def getNucleusId(self, lab):
        nuc = self.nuclei.get(lab)
        if nuc is not None and nuc.label==lab:
            return lab
        for nucid, nuc in self.nuclei.items():
            if nuc.label == lab:
                return nucid
        return -1
    
    def findCellWithLabel(self, lab):
        """ Find the cell that has the corresponding label """
        cell = self.cells.get(lab) 
        # first try if cell of key lab has the same label (usually)
        if cell is not None and cell.label == lab:
            return lab, cell
        for cellid, cell in self.cells.items():
            if cell.label == lab:
                return cellid, cell
        return -1, None


    def reset(self):
        self.cells = {}
        self.maxcell = 0
        self.nuclei = {}
        self.maxnucleus = 0
        self.association = {}
        self.labels = {}

    def getNucleus(self, nucK):
        if self.nuclei.get(nucK) is None:
            return None
        return self.nuclei[nucK]
    
    def getCell(self, cellK):
        if self.cells.get(cellK) is None:
            return None
        return self.cells[cellK]

    def getAssociatedCellId(self, nucK):
        # try if they have the same label first
        hope = self.association.get(nucK) 
        if hope is not None and hope == nucK:
            return nucK
        for cellid, nucid in self.association.items():
            if nucid == nucK:
                return cellid
        return -1
    
    
    def getAssociatedNucleusId(self, cellK):
        if self.association(cellK) is None:
            return -1
        return self.association[cellK]
    
    def getAssociatedNucleusObj(self, cellK):
        if self.association.get(cellK) is None:
            return None
        return self.nuclei[ self.association[cellK] ]

    def relabelNuclei(self):
        prevlabs = np.copy(self.imgnuc)
        self.imgnuc = np.zeros(self.imgnuc.shape, dtype="uint16")
        cellmax = np.max(self.imgcell)
        for nucid, nucleus in self.nuclei.items():
            cellid = self.getAssociatedCellId(nucid)
            prelabel = nucleus.label
            if cellid > 0:
                nucleus.label = self.getCell(cellid).label
            else:
                nucleus.label = max(cellmax, np.max(self.imgnuc))+1
            #print(str(cellid)+" "+str(prelabel)+" -> "+str(nucleus.label))
            self.imgnuc[prevlabs==prelabel] = nucleus.label

    def relabelUnassociatedNuclei(self, nuclei):
        maxcell = np.max(self.imgcell)
        maxlab = np.max(self.imgnuc)
        maxlab = max(maxlab, maxcell)+1 # sure that it is free
        for nucleus in nuclei:
            if nucleus.label <= maxcell:  # could be a cell with same value
                self.imgnuc[self.imgnuc==nucleus.label] = maxlab
                nucleus.label = maxlab
                maxlab += 1

    def associateNucleusAndRelabel(self, nucleus, cell, celllab=None, nucid=None):
        """ relabel the nucleus as cell """
        if celllab is None:
            celllab = cell.label
        #print("Asso "+str(nucleus.label)+" "+str(celllab))
        prevlabel = (self.imgnuc==celllab)
        # if nucleus label already taken, change it
        if np.sum(prevlabel)>0:
            prevnucleus = self.getNucleusId(celllab)
            newlabel = np.max(self.imgnuc)
            newlabel = max(newlabel, np.max(self.imgcell))+1
            self.imgnuc[prevlabel] = newlabel
            self.nuclei[prevnucleus].label = newlabel
        self.imgnuc[self.imgnuc==nucleus.label] = celllab
        nucleus.label = celllab
        if nucid is None:
            nucid  = self.getNucleusId(nucleus.label)
        self.association[self.getCellId(celllab)] = nucid

    def associateCNLabels(self, nuclab, celllab):
        nucid = self.getNucleusId(nuclab)
        if nucid >= 0:
            nucleus = self.nuclei[nucid]
            self.associateNucleusAndRelabel(nucleus, None, celllab, nucid)

    def associateNucleusWithCell(self, nucleusK, cellK, scaleXY, scaleZ ):
        """ Associate nucleus of key nucleusK with cell of key cellK """
        self.association[cellK] = nucleusK
        if cellK in self.cells.keys():
            nucleus_measures = self.nuclei[nucleusK].getMeasures( scaleXY, scaleZ )
            self.cells[cellK].addMeasures( nucleus_measures )

    def getCellFromCoord( self, coord ):
        """ Get the cell from the coordinates """
        if self.imgcell is None:
            return None
        if len(coord) > 2:
            coord = coord[1:]
        return self.imgcell[int(floor(coord[0])), int(floor(coord[1]))]

    def createCellsFromResults( self, results, direction=-1, talkative=True ):    
        """ Initialize the cells from the results table """
        self.reset()
        for rlab, r in results.items():
            cell = Cell( label=r["CellLabel"], area=r["CellAreaMicron2"], center=(r["YPosPixel"], r["XPosPixel"]) )
            cell.setDirection( direction )
            cell.loadResults( r )
            if "ZPosPixel" in r.keys():
                cell.setZJunction( r["ZPosPixel"] )
            self.addLabeledCell( cell, rlab )
        if talkative:
            print(str(len(self.cells.keys()))+" apical cells loaded from previous results")
            
    def createCellsFromMask(self, mask, zo1, results, find_z = True, zmap=None, cells_direction=-1, talkative=True):
        """ Create the cells from a 2D labelled image and previous results """
        self.reset()
        self.imgcell = mask
        regions = regionprops( mask )
        if talkative:
            print("Creating "+str(len(regions))+" cells...")

        ## Create cells
        direction = np.sign( cells_direction )
        for r in regions:
            cell = Cell( label=r.label, area=r.area, center=r.centroid, bbox=r.bbox )
            cell.setDirection( direction )

            if (results is not None) and (results != {}):
                if r.label in results.keys():
                    ## check if cell was not modified, then load it
                    if int(r.centroid[1]) == int(float(results[r.label]["XPosPixel"])):
                        if int(r.centroid[0]) == int(float(results[r.label]["YPosPixel"])):
                            cell.loadResults( results[r.label] )
                else:
                    for rlab in results.keys():
                        ## check if there is a similar cell, then load it
                        if int(r.centroid[1]) == int(float(results[rlab]["XPosPixel"])):
                            if int(r.centroid[0]) == int(float(results[rlab]["YPosPixel"])):
                                cell.loadResults( results[rlab] )
                                break


            if (find_z and "ZPosPixel" not in cell.getMeasuresKeys()) or (find_z and cell.getMeasure("ZPosPixel")<0):
                if zmap is not None:
                    cell.setZJunctionsFromMap(zmap)
                else:
                    cell.setZJunctions(zo1)

            self.addLabeledCell( cell, r.label ) 
        if talkative:
            print(str(len(self.cells.keys()))+" apical cells ")

    def cellsHaveZPos( self ):
        """ Check if the majority of the cells have a Z position """
        nok = 0
        for cellid, cell in self.cells.items():
            if cell.hasZpos():
                nok += 1
            if nok > len(self.cells)/2:
                return True
        return False

    def updateCellsZPosFromMap(self, zmap):
        """ Update the position of the cells from the zmap """
        for cellid, cell in self.cells.items():
            cell.setZJunctionsFromMap(zmap)

    def updateCellZPos(self, cell_label, zpos, img=None, scaleZ=1):
        """ Update the z position of the given cell """
        cellid, cell = self.findCellWithLabel(cell_label)
        ## erase the cell if image
        if img is not None:
            img[cell.zjunc, self.imgcell==cell.label] = 0
        cell.updateZJunction( zpos, scaleZ )
        # if image, update its drawing
        if img is not None:
            img[cell.zjunc,] = img[cell.zjunc,] + cell.label*(self.imgcell==cell.label)
    
    def updateCellsZPosFromList(self, zlist):
        """ Update the position of the cells from the list of cells z """
        for cellid, cell in self.cells.items():
            cell.setZJunctionsFromList(zlist)
    
    def updateCellsZPosFromDictList(self, zlist):
        """ Update the position of the cells from the list of dict of cells z """
        for cellrow in zlist:
            cell_label = int(cellrow["CellLabel"])
            cellid, cell = self.findCellWithLabel(cell_label)
            if cellid is not None:
                for zposname in ["ZPosPixel", "ZPos"]:
                    if cellrow.get(zposname) is not None:
                        cell.setZJunction( int(cellrow[zposname]) )

    def createCellsFrom3DLabels( self, imgJun, cells_direction=-1, verbose=True ):
        """ Create the cells from the 3D labelled image """
        self.reset()
        self.imgcell = imgJun
        ## exclu label 1 pour unassigned
        if np.sum(imgJun == 1) > 0:
            imgJun[imgJun==1] = np.max(imgJun)+1
        direction = np.sign(cells_direction)
        for z in range(imgJun.shape[0]):
            regions = regionprops(imgJun[z,])
            ## Create cells
            for r in regions:
                cell = Cell(r, label=r.label, area=r.area, center=r.centroid, bbox=r.bbox)
                cell.zjunc = z
                cell.setDirection(direction)
                self.addLabeledCell(cell, r.label)
        if verbose:
            print(str(len(self.cells.keys()))+" cells ")

    ## write z positions to file
    def getCellsZDict( self ):
        """ Write Z positions of the cells to file """
        results = []
        for cellid, cell in self.cells.items():
            cellres = cell.writeZ()
            results.append(cellres)
        return results

    ## associate nuclei with cells
    def associateCellsNuclei(self, association_limit, scaleXY, scaleZ, verbose=True, pbar=None):
        """ Associate contours and nuclei by distance """
        associate_nucleiToCell(self, self.imshape[1:3], dlim=association_limit, scaleXY=scaleXY, scaleZ=scaleZ, pbar=pbar)  ## distance scaled
        if verbose:
            print("Associated "+str(len(self.association.keys()))+" junctions with nuclei")
    
    def reset_nuclei( self, asso=True ):
        """ Reset nuclei and association values """
        self.nuclei = {}
        if asso:
            self.association = {}
            for cellid, cell in self.cells.items():
                cell.remove_measures( "Nuclei", start=True )


    def createNucleiFromMask( self, associate=True, verbose=True, scaleXY=1, scaleZ=1 ):
        self.maxnucleus = 1
        self.reset_nuclei( asso=True )
        regions = regionprops( self.imgnuc )
        for r in regions:
            nucleus = Nucleus( label=r.label, volume=r.area, center=r.centroid, bbox=r.bbox )
            self.addLabeledNucleus( nucleus, r.label, associate, scaleXY, scaleZ )
        if verbose:
            print("Nb nuclei found: "+str(len(self.nuclei.keys())))
            if associate:
                print("Nb of associated nuclei: "+str(len(self.association.keys())))
   
    def drawCellsJunc3D( self, zo1, full=True, thick=1 ):
        """ Draw 3D stack of cells junctions, placed at their estimated Z """
        print("Drawing cells in 3D")
        imgJun = np.zeros(self.imshape, dtype="uint16") 
        if not full:
            bound = find_boundaries( self.imgcell, mode="inner" )
        for cellid, cell in self.cells.items():
            label = cell.label
            z = cell.zjunc
            if z == -99999:
                print("Recalculates Z for cell "+str(label))
                cell.setZJunctions( zo1 )
                z = cell.zjunc
            ## if full, draw the whole cell, else only the contour
            if full:
                imgJun[z][self.imgcell==label] = label
            else:
                imgJun[z][(self.imgcell==label) * bound] = label
        if not full:
            if thick > 1:
                imgJun = expand_labels( imgJun, distance=thick )
        return imgJun


    def drawCellsHull(self):
        imgHull = np.zeros(self.imshape, dtype="uint16")
        for cellid, cell in self.cells.items():
            nuc = self.getNucleus( cell.label )
            if nuc is not None:
                bbox = ut.mergeBoundingBox( cell.bbox, cell.zjunc, nuc.bbox )
                imgHull[bbox[0]:bbox[3],bbox[1]:bbox[4], bbox[2]:bbox[5]] = imgHull[bbox[0]:bbox[3],bbox[1]:bbox[4],bbox[2]:bbox[5]] + cell.label*self.drawHull(cell, nuc, bbox)
        return imgHull

    
    def resetCellCounts(self, name=None, zero=False):
        """ reset the cell counts """
        for cell in self.cells.values():
            if name is None:
                cell.resetCounts()
            else:
                cell.resetCount(name, zero)

    def getMeasureEmptyNucleus( self ):
        result = {}
        result["NucleusID"] = -9999
        result["NucleusLabel"] = -9999
        result["NucleusVolumeInMicron3"] = -9999
        result["NucleusZPositionInMicron"] = -9999
        result["NucleusZPositionInPixels"] = -9999
        result["NucleusXPosInPixels"] = -9999
        result["NucleusYPosInPixels"] = -9999
        return result
    
    def noinitMeasureCell(self, result):
        result["CellId"] = []
        result["CellLabel"] = []
        result["CellAreaMicron2"] = []
        result["XPosPixel"] = []
        result["YPosPixel"] = []
        result["ZPosPixel"] = []
        result["XPosMicron"] = []
        result["YPosMicron"] = []
        result["ZPosMicron"] = []
    
    def noaddInitMeasureCytoplasmic( self, cytochannels, result ):
        for cyt in cytochannels:
            result["Cyto"+str(cyt)+"_MeanIntensity"] = []
            result["Cyto"+str(cyt)+"_StdIntensity"] = []
            result["Cyto"+str(cyt)+"_MedianIntensity"] = []
            result["Cyto"+str(cyt)+"_MeanNormalisedIntensity"] = []
            result["Cyto"+str(cyt)+"_StdNormalisedIntensity"] = [] 
            result["Cyto"+str(cyt)+"_MedianNormalisedIntensity"] = []
            result["Cyto"+str(cyt)+"_SumIntensity"] = []
            result["Cyto"+str(cyt)+"_SumNormalisedIntensity"] = []
    
    def getResults( self, scaleXY, scaleZ ):
        results = []
        for cellid, cell in self.cells.items():
            cell.measureCell( cellid, scaleXY, scaleZ )
            cellres = cell.getMeasures()
            ## look for nuclei measures if there are any
            if ("NucleusID" not in cellres) or (cellres["NucleusID"]<0) or (cellres["NucleusLabel"]<0):
                if self.association.get(cellid) is not None:
                    nucid = self.association.get(cellid)
                    cell.putMeasure( "NucleusID", nucid )
                    cell.addMeasures( self.nuclei[nucid].getMeasures( scaleXY, scaleZ ) )
                else:
                    cell.addMeasures( self.getMeasureEmptyNucleus() )
                ## update measures
                cellres = cell.getMeasures()
                #print(cellres)

            ## add measures of RNA counts
            cellrna = cell.getCounts()
            for key, val in cellrna.items():    
                if key != "CellLabel":
                    cellres[key] = val
            ## add features value 
            cellfeat = cell.getFeatures()
            for key, val in cellfeat.items():
                cellres[key] = val  
            results.append(cellres)
        return results
    
    def filterNuclei( self, minvol, minnbz, scaleVolume, verbose=True ):
        regions = regionprops( self.imgnuc )
        print("Going to filter "+str(len(regions))+" nuclei")
        for r in regions:
            ## in less than minz slices, too small, remove
            if (r.bbox[3]-r.bbox[0]) < minnbz:
                self.imgnuc[r.bbox[0]:r.bbox[3], r.bbox[1]:r.bbox[4], r.bbox[2]:r.bbox[5]][r.image] = 0
            # remove if smaller than minimum volume
            else:
                vol = r.area*scaleVolume
                if vol < minvol:
                    self.imgnuc[r.bbox[0]:r.bbox[3], r.bbox[1]:r.bbox[4], r.bbox[2]:r.bbox[5]][r.image] = 0
                    if len(self.nuclei) > 0:
                        nid = self.getNucleusId(r.label)
                        if nid > 0:
                            del self.nuclei[nid]

        if verbose:
            print("Nb nuclei kept: "+str(len(np.unique(self.imgnuc))-1))
    
    def distanceNucleusToCell(self, nucleus, cell, scalexy, scalez):
        """ distance between a nucleus and a cell """
        cellpt = cell.juncCenter()
        # check if contact
        if self.imgnuc[int(cellpt[0]), int(cellpt[1]), int(cellpt[2])]==nucleus.label:
            #print("inside "+str(nucleus.label)+" "+str(cell.label))
            return 0.001  ## contour center is inside nucleus
        
        # distance center to center
        dist = cell.distance3D2center( nucleus.center, scalexy, scalez )
        dist = dist + cell.distance2center( (nucleus.center[1], nucleus.center[2]) )*scalexy # penalize distance in xy
        return dist
    
    ######################################################
    ####### Cytoplasmic measures
    def measureCellsCytoplasmic( self, cytoThickness, cytochannels, imagesCyto, meanbgints, scaleXY, scaleZ ):
        results = []
        for cellid, cell in self.cells.items():
            if cell.getMeasures() == {}:
                cell.measureCell( cellid, scaleXY, scaleZ )
            
            if "NucleusID" not in cell.getMeasures():
                if self.association.get(cellid) is not None:
                    nucid = self.association.get(cellid)
                    cell.putMeasure( "NucleusID", nucid )
                    cell.addMeasures( self.nuclei[nucid].getMeasures( scaleXY, scaleZ ) )
                else:
                    cell.addMeasures( self.getMeasureEmptyNucleus() )

            cell.addMeasuresCytoplasmic( cellmask=(self.imgcell==cell.label), cytoThickness=cytoThickness, cytochannels=cytochannels, imagesCyto=imagesCyto, meanbgints=meanbgints )
            results.append( cell.getMeasures() )
        return results

    def measureAppendPrevious( self, results, previous_results, columns ):
        """ Append the previous results (if any) to the current results """
        full_results = []
        for row in results:
            cellid = row["CellId"]
            for prevrow in previous_results:
                if prevrow["CellId"] == str(cellid):
                    for key in columns:
                        if prevrow[key] is not None:
                            row[key] = prevrow[key]
                    break
            full_results.append(row)
        return full_results

    
    def drawProjectedCyto(self, results, column):
        imgProj = np.zeros(self.imshape[1:3], dtype="float32")
        for res in results:
            celllab = int(res["CellLabel"])
            mask = np.where(self.imgcell==celllab)
            imgProj[mask] = res[column]
        return imgProj
    
    ##########################################################
    ##### Classify cells

    def loadFeature(self, featname, featimg):
        for cellid, cell in self.cells.items():
            cellmask = (self.imgcell==cell.label)
            val = np.mean(featimg[cellmask])
            cell.putFeature(featname, int(val))

    def drawCellsValues(self, featimg, clusters, values):
        """ Draw in the featimg the cells with labels to values """
        for clus, label in zip(clusters, values):
            cellmask = (self.imgcell==label)
            featimg[cellmask] = clus
    
    def drawFeatureInCells(self, featimg, featname):
        """ Draw in the featimg the cells with the feature values """
        for cellid, cell in self.cells.items():
            value = cell.getFeature(featname)
            if value is not None:
                cellmask, bbox = cell.get_maskBB( self.imgcell )
                featimg[bbox[0]:bbox[2],bbox[1]:bbox[3]][cellmask] = value

    def drawCountsInCells(self, countimg, countname):
        """ Draw in the countimg the cells with the RNA counts values """
        for cellid, cell in self.cells.items():
            value = cell.getCount(countname)
            if value is not None:
                cellmask, bbox = cell.get_maskBB( self.imgcell )
                countimg[bbox[0]:bbox[2],bbox[1]:bbox[3]][cellmask] = value

    def classifyCellsFromBoundaries( self, featname, border=0, boundary=2 ):
        """ Classificy cells according to their position on border/edge """
        featimg = np.zeros(self.imgcell.shape, np.uint8)
        featimg[ self.imgcell > 0 ] = 1
        bound_labels = []
        border_labels = []
        if boundary > 0:
            bound_labels = ut.get_boundary_cells( self.imgcell, ndil=5 )
        if border > 0:
            border_labels = ut.get_border_cells( self.imgcell, margin=4 )
        for cellid, cell in self.cells.items():
            cell.putFeature( featname, 1 )
            if cell.label in bound_labels:
                featimg = cell.fillFeature( self.imgcell, featname, featimg, boundary )
            if cell.label in border_labels:
                featimg = cell.fillFeature( self.imgcell, featname, featimg, border )
        return featimg


    def classifyCellsFromThreshold( self, featname, proj, threshold_mean, threshold_fill ):
        """ Classify cells in two groups, above/below threshold """
        featimg = np.zeros(self.imgcell.shape, np.uint8)
        pthres = np.mean(proj)*threshold_mean
        thresproj = np.uint8(proj>pthres) #np.zeros(proj.shape) 
        #thresproj[proj>pthres] = 1
        for cellid, cell in self.cells.items():
            cellmask, bbox = cell.get_maskBB( self.imgcell )
            cellposarea = np.sum(thresproj[bbox[0]:bbox[2], bbox[1]:bbox[3]][cellmask])
            cellarea = np.sum(cellmask>0)
            val =  1 + 1*(cellposarea/cellarea > threshold_fill)
            cell.putFeature(featname, val)
            featimg[bbox[0]:bbox[2],bbox[1]:bbox[3]][cellmask] = val
        return featimg

    def fill_measure(self, featname, value):
        for cellid, cell in self.cells.items():
            cell.putFeature(featname, value)

    def getFeatureCellValue( self, featname, lab ):
        cellid, cell = self.findCellWithLabel(lab)
        return cell.getFeature(featname)

    def getMaxFeature(self, featname):
        """ Get max value of chosen feature """
        featlist = self.getFeaturesHeading()
        if (featlist is None) or (featname not in featlist):
            print("Feature "+featname+" not already measured")
            return None
        cmax = 0
        for cellid, cell in self.cells.items():
            val = cell.getFeature(featname)
            if val is not None and val > cmax:
                cmax = val
        return cmax

    def putFeatureCellValue( self, featname, lab, value ):
        cellid, cell = self.findCellWithLabel(lab)
        if cell is not None:
            cell.putFeature(featname, value)
    
    def changeFeatureCellValue( self, featname, lab, value, featimg ):
        """ Update the cell feature value and redraw it """
        cellid, cell = self.findCellWithLabel(lab)
        if cell is not None:
            cell.putFeature(featname, value)
            bbox = cell.bbox
            cellmask = ( (self.imgcell[bbox[0]:bbox[2], bbox[1]:bbox[3]])==lab )
            featimg[bbox[0]:bbox[2],bbox[1]:bbox[3]][cellmask] = value
    
    def addCytoplasmicValue( self, rowdict ):
        """ Add cytoplasmic value from given row to the corresponding cell """
        rowdict = ut.strip_keys( rowdict )
        cell_label = int( float(rowdict["CellLabel"]) )
        ## check that the cell exists and is the same
        cellid, cell = self.findCellWithLabel( cell_label )
        if cell is None:
            return
        posxname = "XPosPixel"
        posyname = "YPosPixel"
        if posxname not in rowdict.keys():
            posxname = "XPosInPixels"
            posyname = "YPosInPixels"
            if posxname not in rowdict.keys():
                print("Column name "+str(posxname)+" not found in cytoplasmic table. Rename column if necessary" )
                return
        if int(float(cell.centerXY[1])) != int(float(rowdict[posxname])):
            return
        if int(float(cell.centerXY[0])) != int(float(rowdict[posyname])):
            return
        for feat in rowdict.keys():
            if feat != "CellId" and feat != "CellLabel":
                if feat.startswith("Cyto"):
                    if rowdict[feat] == "":
                        cell.putMeasure( feat, -99999)
                    else:
                        cell.putMeasure( feat, float(rowdict[feat]) )

    def addFeatureValue( self, rowdict ):
        cell_label = int(rowdict["CellLabel"])
        for feat in rowdict.keys():
            if feat != "CellId" and feat != "CellLabel":
                featname = feat
                if not feat.startswith("Feat_"):
                    featname = "Feat_"+feat
                self.putFeatureCellValue( featname, cell_label, floor(float(rowdict[feat])) )

    def getFeaturesHeading(self):
        """ Return list of measures """
        firstk = next(iter(self.cells))
        keys = []
        for cellid, cell in self.cells.items():
            ckeys = cell.getFeaturesKeys()
            keys = list(set(keys).union(ckeys))
        return keys

    def getFeaturesTable( self ):
        tab = {}
        keys = []
        ## ensure that all possible keys are present (in case it's missing the first cell)
        for cellid, cell in self.cells.items():
            ckeys = cell.getFeaturesKeys()
            for k in ckeys:
                if k not in keys:
                    keys.append(k)
        tab["CellId"] = []
        tab["CellLabel"] = []
        for k in keys:
            tab[k] = []
        for cellid, cell in self.cells.items():
            meas = cell.getFeatures()
            tab["CellId"].append(cellid)
            tab["CellLabel"].append(cell.label)
            for k in keys:
                ## put 0 if not present
                if k not in meas:
                    tab[k].append(0)
                else:
                    tab[k].append(meas[k])
        return tab

    ######################################################
    ##### RNA assignation
    def distance3D(self, pta, ptb, scaleXY, scaleZ):
        return sqrt( pow(pta[0]-ptb[0],2)*scaleZ*scaleZ + pow(pta[1]-ptb[1],2)*scaleXY*scaleXY + pow(pta[2]-ptb[2],2)*scaleXY*scaleXY )
   
    def add_onespot(self, cell, name):
        if cell is not None:
            if name is not None:
                cell.addCount(name,1)
    
    def rna2projection(self, pt, distZlim, scaleXY, scaleZ, above=1, prejuge=-1):
        """ assign RNA in z-projected cell """
        # look at label image value
        celllab = self.imgcell[ pt[1], pt[2] ]
        if celllab == 0:
            return None, -1, 0
        else:
            cellid, cell = self.findCellWithLabel( celllab )

        if cell is not None:
            disz = cell.verticalDistance( pt, scaleZ )
            ## Assignement score: 1 if in the cell (same Z)
            if disz == 0:
                score = 1
            else:
                ## Otherwise ratio between distance and cell mean radius
                disxy = cell.distance2center( (pt[1], pt[2]) )*scaleXY 
                distance = sqrt(disxy*disxy+disz*disz)
                meanrad = cell.mean_radius()*scaleXY 
                score = max( 1-distance/meanrad, 0 )
            
            if not cell.aboveCell(pt, dz=above):
                ## in the cell
                if disz <= distZlim:
                    return cell, disz, score
            ## not in the good half (above) or too far
            return None, disz, 0
        return None, -1, 0
    
    def getCropBox(self, pt, margins, img):
        lims = []
        for i in range(3):
            mini = pt[i]-margins[i]
            maxi = pt[i]+margins[i]
            mini = max(mini, 0)
            maxi = min(maxi, img.shape[i])
            lims.append(int(mini))
            lims.append(int(maxi))
        return lims

    ### Method closest nuclei
    def rna2closestNuclei(self, pt, dlim, scaleXY, scaleZ, above=1, prejuge=-1):
        """ 
            Find closest nuclei (surface) and add rna to the corresponding cell
            Don't add if distance too big compared to threshold dlim
        """
        ## if inside a nucleus, direct
        hope = self.imgnuc[pt]
        if hope > 1:
            icell = self.getAssociatedCellId( hope )
            cell = self.getCell(icell)
            return (cell, 0, 0, 1)
        
        margins = (dlim/scaleZ+1, dlim/scaleXY+1, dlim/scaleXY+1)
        crop = self.getCropBox(pt, margins, self.imgnuc)
        ptcrop = (pt[1]-crop[2], pt[2]-crop[4])
        ## non isotropic so calculate slice by slice
        dist = 100000
        best_nuclei = -1
        distinz = -1
        for z in range(crop[0], crop[1]):
            zcrop = self.imgnuc[z, crop[2]:crop[3], crop[4]:crop[5]]
            if np.sum(zcrop)>0:
                ## distance_transform is distance to closest background, so inverse
                dist2lab, nearest_coord = distance_transform_edt(zcrop==0, return_indices=True)
                nearest_pt = [ nearest_coord[dim][ptcrop] for dim in range(2) ]
                best_dist = dist2lab[ptcrop]
                bestnuclei = zcrop[tuple(nearest_pt)]
                npt = (z, nearest_pt[0]+crop[2], nearest_pt[1]+crop[4])
                curdist = self.distance3D( npt, pt, scaleXY, scaleZ )
                if curdist < dist:
                    dist = curdist
                    distinz = abs(pt[0]-z)*scaleZ
                    best_nuclei = best_nuclei
        
        if best_nuclei > 1:
            ibestcell = -1
            bestcell = None
            if dist < dlim:
                ## found match, add the RNA to this cell if associated
                ibestcell = self.getAssociatedCellId( best_nuclei )
                bestcell = self.getCell(ibestcell)

            if bestcell is not None and not bestcell.aboveCell(pt, dz=above):          
                meanrad = sqrt(bestcell.area/pi)
                score = 1-dist/meanrad
                if score < 0:
                    score = 0
                return (bestcell, distinz, dist, score)
            else:
                return(None,-1,-1, 0)
        
        return (None,-1,-1, 0)


   ### not updated

    def drawProjectedNucleiCenter(self, img, associated=None, size=2):
        if associated is None:
            for nucid, nucleus in self.nuclei.items():
                nucleus.drawProjectedCenter(img, label=self.labels["Nucleus_"+str(nucid)], size=size)
        else:
            if associated:
                for cellid, nucid in self.association.items():
                    self.nuclei[nucid].drawProjectedCenter(img, label=self.labels["Nucleus_"+str(nucid)], size=size)
            else:
                for nucid, nucleus in self.nuclei.items():
                    if self.association.get(nucid) is None:
                        nucleus.drawProjectedCenter(img, label=self.labels["Nucleus_"+str(nucid)], size=size)
    
    def drawRNACountProj(self, method):
        rnas = np.zeros(self.imshape[1:3], dtype=np.uint16)
        for cell in self.cells.values():
            col = cell.getCount(method)
            # to update if want
            #rnas = drawContourFilled(cell.contour, rnas, int(col))
        return rnas
    
    def getMeanCellsZ(self):
        mean = 0
        n = 0
        for cell in self.cells.values():
            mean += cell.zjunc
            n += 1
        if n == 0:
            return 0
        return (mean*1.0/n)
    
    def getMeanNucleiZ(self):
        mean = 0
        n = 0
        for nuc in self.nuclei.values():
            mean += nuc.center[0]
            n += 1
        if n == 0:
            return 0
        return (mean*1.0/n)

    def measureCellsCount(self, rnachannels, methods):
        for cellid, cell in self.cells.items():
            cell.addCountResults( rnachannels, methods )

    def getCounts( self ):
        """ Get the counts of the cells """
        results = []
        for cellid, cell in self.cells.items():
            cellres = cell.getCounts()
            cellres["CellLabel"] = cell.label
            results.append(cellres)
        return results
    
    def measureOnlyCellsCount(self, rnachannels, methods, scaleXY, scaleZ):
        results = []
        for cellid, cell in self.cells.items():
            cellres = cell.measureOnlyCellLabel()
            for ir, rnac in enumerate(rnachannels):
                if type(methods) == list:
                    cmethod = methods[ir]
                else:
                    cmethod = methods
                cellres[cmethod] = cell.getCount(cmethod)
            results.append(cellres)
        return results
    
    def measureNuclearStaining( self, img, chan ):
        """ Measure signal inside segmented nuclei """
        results = []
        for nucid, nucleus in self.nuclei.items():
            lab = nucleus.label
            nucres = nucleus.measureIntensity( self.imgnuc==lab, img, chan )

            if self.association != {}:
                cellid = self.getAssociatedCellId(nucid)
                if cellid >= 0:
                    self.cells[cellid].addMeasures( nucres )
            nucres["NucleusID"] = nucid
            nucres["NucleusLabel"] = nucleus.label
            results.append(nucres)
        return results


    def populationBoundingBox( self, dlim, above ):
        boundbox = [100000, -1, 100000, -1, 100000, -1]
        print("to update")
        return boundbox

    
    def tryCell( self):
        together = self.drawCellsJunc3D()
        together[together==0] = self.imgnuc[together==0]
        regions = regionprops(together)
        for r in regions:
            together[r.bbox[0]:r.bbox[3], r.bbox[1]:r.bbox[4], r.bbox[2]:r.bbox[5]][r.image_convex] = r.label
            #together[r.bbox[0]:r.bbox[3], r.bbox[1]:r.bbox[4], r.bbox[2]:r.bbox[5]][r.image_filled] = r.label
        return together

##################################################################

    ### Test method : inside hull
    def drawHull(self, cell, nucleus, bbox):
        """ draw Hull area between junctions and nuclei """
        nangles = 180
        dang = 360/nangles
        cellAngPts = cell.angleContour( dang, self.imgcell[bbox[1]:bbox[4],bbox[2]:bbox[5]]==cell.label, bbox)
        nucAngPts = nucleus.angleContour( dang, self.imgnuc[bbox[0]:bbox[3],bbox[1]:bbox[4],bbox[2]:bbox[5]]==nucleus.label, bbox)
        
        imgHull = np.zeros((bbox[3]-bbox[0], bbox[4]-bbox[1], bbox[5]-bbox[2]), dtype="uint16")
        zcur = int(cell.zjunc)-bbox[0]
        zjunc = cell.zjunc-bbox[0]
        zend = int(nucleus.center[0])-bbox[0]
        while zcur != zend:
            for cellpt, nucpt in zip(cellAngPts, nucAngPts):
                if cell.zjunc == zend:
                    if zcur == cell.zjunc:
                        ratio = 0
                    else:    ## both nuclei and junc same z
                        return None, 0
                else:
                    ratio = (zcur-zjunc)*1.0/(zend - zjunc)
               
                ptx = cellpt[0]*(1-ratio) + ratio*nucpt[0]
                pty = cellpt[1]*(1-ratio) + ratio*nucpt[1]
                #print(str(zcur)+" "+str(zend)+" "+str(cellpt[0])+" "+str(cellpt[1])+" "+str(nucpt[0])+" "+str(nucpt[1]))
                imgHull[zcur, int(ptx), int(pty)] = 1
            imgHull[zcur,] = convex_hull_image(imgHull[zcur,])
            #struc = generate_binary_structure(2,2)
            #struc = iterate_structure(struc, 10)
            #imgHull[zcur,] = binary_closing(imgHull[zcur,], struc)
            zcur += int(np.sign(zend-zcur)*1)
        return imgHull

    def initializeHull(self, angular_step):
        """ Initialize hull contours, only associated cells """
        for cellid, nucid in self.association.items():
            self.cells[cellid].calcProjContour( angular_step, self.imgcell==self.cells[cellid].label )
            nucimg = self.imgnuc == self.nuclei[nucid].label
            self.nuclei[nucid].calcProjContour( angular_step, nucimg, self.cells[cellid] )
    
    def getAngle(self, d1, d2):    
        ang = atan2(d2,d1)   ## results between -pi and pi -> put to 0,360
        if ang < 0: 
            ang = pi+(abs(pi+ang))
        ang = ang*180/pi
        if ang >= 360:
            ang = ang-360
        return ang
    
    def rna2insideHull(self, pt, dang, name="Hull", scaleXY=1):
        """
        works only on associated cells
        assignement score: at current slice, get center, current radius for the point angle et compare distance: (dhull - dpt/2)/dhull => if closer than dhull (radius), > 0.5, outside < 0.5 to 0 at 2 dhull
        """
        dis2hull = 100000
        bestind = -1
        bestscore = 0

        for cellid, cell in self.cells.items():
            bbox = cell.bbox
            if bbox is None:
                print("Empty bounding box")
                return
        
            ## if cell is associated
            if self.association.get(cellid) is not None:
                
                ## check if close to the cell, margin is in pixels
                if ut.insideBoundingBox((int(pt[1]), int(pt[2])), bbox, margin=50):
                    cellcenter = (cell.zjunc, cell.centerXY[0], cell.centerXY[1])
                    nucleus = self.getAssociatedNucleusObj(cellid)
                    if self.imgnuc[ int(pt[0]), int(pt[1]), int(pt[2]) ] == nucleus.label:
                        return cell, 0, 0, 1 # inside nucleus

                    curcenter, ratio = nucleus.interpCenter(cellcenter, pt[0], ext=0.5)
                    # is potentially inside the cell
                    if curcenter is not None:
                        d1 = pt[1]-curcenter[1]
                        d2 = pt[2]-curcenter[2]
                        ang = self.getAngle(d1,d2)
                        indang = int(ang/dang)
                        
                        ptnucleusxy = nucleus.projAnglePoints[indang]
                        ptjuncxy = cell.projAnglePoints[indang]
                        curpt = [ptjuncxy[0], ptjuncxy[1]]   ## interpolated point
                        for i in range(1):
                            curpt[i] += ratio*(ptnucleusxy[i]-ptjuncxy[i])
                        dcurpt = sqrt(pow(curpt[0]-curcenter[1],2) + pow(curpt[1]-curcenter[2],2))   ## distance sq interp to center
                        dpt = sqrt(pow(d1,2) + pow(d2,2))   ## distance sq pt to center
                        score = max( (dcurpt - dpt/2)/(dcurpt), 0 )
                        #### if closer to center, pt is inside the cell
                        if dpt < dcurpt:
                            return cell, 0, 0, score
                        else:                        ### closest hull
                            if (dpt-dcurpt)<dis2hull:
                                dis2hull = (dpt-dcurpt)*scaleXY  ## distance in the XY plane
                                bestind = cellid
                                bestscore = score

        return None, dis2hull, bestind, bestscore
    

    def assign_onespot(self, spot, method, distanceLim, above=1, angular_step=0, nchannel=0, countName="", scaleXY=1, scaleZ=1, prejuge=-1):
        """ Assing one RNA spot with the given method, and returns the corresponding cell and score of assignement """
        pt = (int(spot[0]), int(spot[1]), int(spot[2]))
    
        if method == "Projection":
            cell, dist, score = self.rna2projection(pt, distanceLim, scaleXY=scaleXY, scaleZ=scaleZ, above=above, prejuge=prejuge)   
            ## add the spot to the corresponding cell
            self.add_onespot(cell, countName)
            return cell, None, score
        
        if method == "ClosestNucleus":
            if self.imgnuc is None:
                ut.show_warning("No nuclei loaded, cannot use this method")
                return
            cell, closdisz, dist, score = self.rna2closestNuclei( pt, dlim=distanceLim, scaleXY=scaleXY, scaleZ=scaleZ, above=above, prejuge=prejuge)
            ## add the spot to the corresponding cell
            self.add_onespot(cell, countName)
            return cell, None, score 

        if method == "Hull":
            cell, dist2h, cellh, score = self.rna2insideHull( pt, dang=angular_step, name=countName, scaleXY=scaleXY )
            self.add_onespot(cell, countName)
            return cell, dist2h, score

        if method == "MixProjClosest":
            ## Mix method: near junctions, projection, below closest nuclei
            cell, dist, score = self.rna2projection(pt, distanceLim, scaleXY=scaleXY, scaleZ=scaleZ, above=above, prejuge=prejuge)
            closcell, closdisz, closdist, score = self.rna2closestNuclei( pt, dlim=distanceLim, scaleXY=scaleXY, scaleZ=scaleZ, above=above, prejuge=prejuge)
            score = dist
            #print("MixPrjClose score to define")
            if cell is None and closcell is None:
                return None, None, 0

            ## found only projection
            if cell is not None and closcell is None:
                self.add_onespot(cell, countName)
                return cell, None, score
                
            ## found only nucleus
            if cell is None and closcell is not None:
                self.add_onespot(closcell, countName)
                return closcell, None, score
    
            ## pt closer in z to nucleus than junction
            if closdisz < dist:
                self.add_onespot(closcell, countName)
                return closcell, None, score
            else:
                ## point closer to junction than nucleus
                self.add_onespot(cell, countName)
                return cell, None, score
                
        print("Assignment method "+method+" not implemented")
        return -1, None, 0 

