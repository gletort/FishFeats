import numpy as np
import os, time
from math import floor
import csv
from skimage.exposure import adjust_gamma
import skimage.metrics as imetrics
import fish_feats.Utils as ut
from fish_feats.CellObjects import Population

try:
    from fish_feats.SegmentObj import local_max_proj, prepJunctions, segmentJunctions
    from fish_feats.RNASpots import RNASpots
except ImportError:
    print("Module missing")
    
####### Z map functions
def score_each_z( img3d, projimg ):
    """ Compare each z image to the projected image """
    best_score = [0,0]
    for z, zslice in enumerate(img3d):
        score = imetrics.normalized_mutual_information(zslice, projimg)
        if best_score[0] < score:
            best_score[0] = score
            best_score[1] = z
    return best_score[1]

def process_x(x, step, projimg, img, winsize):
    """ Process all the image and construct the zmap """
    xstep = step

    if (x+xstep) > projimg.shape[0]:
        xstep = projimg.shape[0]-x
    zmap_x = np.zeros((xstep,projimg.shape[1]), "uint8")
    xmin = x-int(winsize/2)
    if xmin < 0:
        xmin = 0
    xmax = xmin+winsize
    if xmax > projimg.shape[0]:
        xmax = projimg.shape[0]
        xmin = projimg.shape[0]-winsize
    for y in range(0,projimg.shape[1],step):
        ymin = y-int(winsize/2)
        if ymin < 0:
            ymin = 0
        ymax = ymin+winsize
        if ymax > projimg.shape[0]:
            ymax = projimg.shape[0]
            ymin = projimg.shape[0]-winsize

        img3d = img[:,xmin:xmax,ymin:ymax]
        proj = projimg[xmin:xmax,ymin:ymax]
        bestz = score_each_z(img3d, proj)
        zmap_x[:,y:(y+step)] = bestz
    return zmap_x

class MainImage:
    """ Handle the main (original) image (scaling, channels), interface with other analysis """

    def __init__(self, talkative =True):
        self.scaleXY = 1.0
        self.scaleZ = 1.0
        self.junchan = 0
        self.nucchan = 0
        self.nbchannels = 1
        self.verbose = talkative
        self.zdirection = -1
        self.pop = None
        self.nucstain = None
        self.junstain = None
        self.junmask = None
        self.nucmask = None
        self.model = None
        self.rnas = {}
        self.imshape = (0,0,0)
        self.imagename = None
        self.imagedir = None

    def set_imagename(self, imagename):
        """ Set the name and path of the image """
        self.imagename, self.imagedir, self.resdir = ut.extract_names( imagename )
        self.pop = Population( imageshape=(0,0,0) )

    def set_scales( self, scaleZ, scaleXY ):
        """ Set the scales for the image """
        self.scaleXY = scaleXY
        self.scaleZ = scaleZ

    def get_image_path( self ):
        """ Returns the full image name and directory """
        if self.imagename is None:
            return ""
        if self.imagedir is None:
            return ""
        return os.path.join(self.imagedir, self.imagename)

    def set_image_path(self, imgpath=None):
        """ Set the image name and result directory """
        self.imagename, self.imagedir, self.resdir = ut.extract_names( imgpath )

    def crop_name( self ):
        """ build default crop name """
        return os.path.join( self.imagedir, self.imagename+"_crop.tif" )

    def set_image( self, images ):
        """ Set the main image (all the channels) from list of images (already opened) """
        self.image = images
        self.nbchannels = len(images)
        self.imshape = images[0].shape
        self.pop = Population(imageshape=self.imshape)

    def open_image(self, filename):
        self.image, self.scaleXY, self.scaleZ, names = ut.open_image(filename, verbose=self.verbose)
        self.imagename, self.imagedir, self.resdir = ut.extract_names( filename )
        self.image = ut.arrange_dims(self.image, verbose=self.verbose)
        self.imshape = self.image[0,].shape
        self.nbchannels = self.image.shape[0]
        self.pop = Population(imageshape=self.imshape)

    def image_2dshape(self):
        if len(self.imshape) == 3:
            return self.imshape[1:]
        return self.imshape
    
    def get_image_shape(self, in2d=True):
        if in2d:
            if self.junmask is not None:
                return self.junmask.shape
            else:
                if self.junstain is None:
                    return None
                return self.junstain.shape[1:]
        else:
            return self.junstain.shape

    def get_coordinates(self, pos):
        """ Get pixel coordinates from tuple of position """
        ind = int(len(pos)==3)
        return ( int(pos[ind]/self.scaleXY), int(pos[ind+1]/self.scaleXY) )

    def free_channel(self):
        for i in range(self.nbchannels):
            if i != self.junchan:
                if i != self.nucchan:
                    return i
        return 0

    def potential_rnas(self):
        """ Return the list of potentially RNA channels (no junctions nor nuclei) """
        channels = []
        for chan in range(self.nbchannels):
            if (chan != self.junchan) and (chan != self.nucchan):
                channels.append(chan)
        return channels

    def get_channel(self, chan):
        #return zarr.array(self.image[chan])
        return self.image[chan]

    def build_filename(self, endname):
        return os.path.join(self.resdir, self.imagename+endname)

    def get_filename(self, endname, ifexist=False):
        """ Return filename if its exist and ifexist True """
        resfile = os.path.join( self.resdir, self.imagename+endname )
        if ifexist:
            if not os.path.exists(resfile):
                return ""
        return resfile

    def save_zcells(self, filename):
        """ Save a file with the list of cells and corresponding Z position """
        print("Saving Z positions of cells in file "+str(filename))
        zdict = self.pop.getCellsZDict()
        if zdict == []:
            ## calculate the z positions if it was not yet done
            self.popFromJunctions()
            zdict = self.pop.getCellsZDict()
        ut.write_dict(filename, zdict)

    def save_image( self, img, imagename=None, hasZ=False, endname=None, imtype="uint16" ):
        if hasZ:
            scaZ = self.scaleZ
        else:
            scaZ = -1
        if imagename is None:
            imagename = self.build_filename(endname)
        if int(np.max( img, axis=None )) >= 65535: 
            imtype="float32"
        ut.writeTif( img, imagename, scaleXY=self.scaleXY, scaleZ=scaZ, imtype=imtype)
        ut.show_info( "Image "+str(imagename)+" saved" )

    def rnacount_filename(self, ifexist=True):
        resfile = os.path.join(self.resdir, self.imagename+"_RNACounts.csv")
        if ifexist:
            if not os.path.exists(resfile):
                return ""
        return resfile

    def save_measures( self, results, endname, keepprevious=True ):
        """ Save the table of measurement to file. If the file already exists, append the new measures if keepprevious """
        if (results is None) or (len(results) == 0):
            return
        resfile = os.path.join( self.resdir, self.imagename+endname )
        if keepprevious and os.path.exists( resfile ):
            results = self.load_measure_file( resfile, results )
        ut.write_dict(resfile, results)
        ut.show_info("Measures saved in file "+str(resfile))

    def save_results( self ):
        """ Save the table of all results to file """
        resfile = self.get_filename( endname="_results.csv", ifexist=False )
        results = self.pop.getResults( self.scaleXY, self.scaleZ )
        if (results is None) or (len(results) == 0):
            return
        ut.write_dict( resfile, results )
        ut.show_info("Results saved in file "+str(resfile))

    def load_results_file( self, resfile ):
        """ Load already measured table if the corresponding file exists """
        rows = {}
        hasZ = False
        with open( resfile, 'r' ) as infile:
            csvreader = csv.DictReader(infile)
            for row in csvreader:
                if "CellLabel" not in row.keys():
                    continue
                if row["CellLabel"] == "":
                    continue
                try:
                    rows[ int(float(row["CellLabel"])) ] = row
                    if ("PosZPixel" in row.keys()) and (int(float(row["PosZPixel"])) > 0 ):
                        hasZ = True
                except:
                    continue
        return rows, hasZ

    def load_from_results( self, resfile ):
        """ Load results from file and create cells"""
        results, hasz = self.load_results_file( resfile )
        if self.pop is None:
            self.pop = Population( imageshape=self.imshape )
        self.pop.createCellsFromResults( results, direction=self.zdirection, talkative=self.verbose )
    
    def load_measure_file( self, resfile, results ):
        """ Load already measured table if the corresponding file exists """
        with open( resfile, 'r' ) as infile:
            columns = results[0].keys()
            csvreader = csv.DictReader(infile)
            rows = []
            for row in csvreader:
                rows.append( row )
            previous_measures = set(rows[0].keys()) - set(columns)
            print(previous_measures)
            if len( previous_measures) > 0:
                print( "Appending previous measures value in the table" )
                results = self.pop.measureAppendPrevious( results, rows, previous_measures )
            return results


    def save_filename(self):
        return os.path.join(self.resdir, self.imagename+".cfg")

    def load_image(self, filename):
        loadedimg, scaleXYm, scaleZm, names = ut.open_image(filename, verbose=self.verbose)
        return loadedimg

    ################# Junctions

    def junction_filename(self, dim=2, ifexist=False):
        end = "_cells2D.tif"
        if dim==3:
            end = "_cells3D.tif"
        return self.get_filename(end, ifexist)
    
    def zcell_filename(self, ifexist=False):
        end = "_cellsZ.csv"
        return self.get_filename(end, ifexist)
    
    def junction_projection_filename(self, ifexist=False):
        end = "_junction_projection.tif"
        return self.get_filename(end, ifexist)

    def getJunctionsProjection(self):
        """ Return the projection of the junction staining """
        projfilename = self.junction_projection_filename(ifexist=True)
        if projfilename != "":
            proj = self.load_image(projfilename)
            return proj

        ## No projection file found, have to redo the projection
        if self.junstain is None:
            return self.prepare_segmentation_junctions()
        
        ## Something failed somewhere
        print("Something failed in calculating/loading the junction projection")
        return None
    
    def getJunctionsImage3D( self, full=True, thick=1 ):
        """ Create a 3D image containing the cell labels at their 3D position"""
        if self.junstain is None:
            self.junstain = self.image[self.junchan,]
        return self.pop.drawCellsJunc3D( self.junstain, full, thick )

    def loadCellsFromSegmentation( self, junfilename ):
        """ Load only the segmentation mask """
        self.junmask, scaleXYm, scaleZm, names = ut.open_image(junfilename, verbose=self.verbose)
        if (self.junmask.dtype == np.float32) or (self.junmask.dtype == np.float64 ):
            self.junmask = self.junmask.astype(np.uint32)
        self.pop = Population(imageshape=self.imshape)
        self.pop.createCellsFromMask(self.junmask, None, None, find_z=False, zmap=None, cells_direction=self.zdirection, talkative=self.verbose)

        ## if cellsZ file exists, load it
        zcellfilename = self.zcell_filename(ifexist=True)
        if zcellfilename != "":
            zcellsDict = ut.load_dictlist(zcellfilename, verbose=self.verbose)
            self.pop.updateCellsZPosFromDictList( zcellsDict )     


    def load_segmentation( self, junfilename ):
        """ Load the segmentation and the sepatated staining if necesary"""
        self.junmask, scaleXYm, scaleZm, names = ut.open_image(junfilename, verbose=self.verbose)
        if (self.junmask.dtype == np.float32) or (self.junmask.dtype == np.float64 ):
            self.junmask = self.junmask.astype(np.uint32)
        if self.junstain is None:
            if self.should_separate():
                separated_junctionsfile = self.separated_junctions_filename(ifexist=True)
                separated_nucleifile = self.separated_nuclei_filename(ifexist=True)
                if (separated_junctionsfile != "") and (separated_nucleifile != ""):
                    self.load_separated_staining( separated_junctionsfile, separated_nucleifile )
                else:
                    print("Should separate the junctions and nuclei staining first")
            else:
                self.junstain = self.image[self.junchan,]
    
    def separated_nuclei_filename(self, ifexist=False):
        end = "_nucleiStaining.tif"
        return self.get_filename(end, ifexist)
    
    def separated_junctions_filename(self, ifexist=False):
        end = "_junctionsStaining.tif"
        return self.get_filename(end, ifexist)
        
    def load_separated_staining(self, junfile, nucfile ):
        """ Load the separated staining from files """
        self.junstain, scaleXYm, scaleZm, names = ut.open_image(junfile, verbose=self.verbose)
        self.nucstain, scaleXYm, scaleZm, names = ut.open_image(nucfile, verbose=self.verbose)

    def separate_junctions_nuclei( self, wth_radxy=4, wth_radz=1, rmoutlier_radxy=5, rmoutlier_radz=1, rmoutlier_threshold=40, smoothnucxy=2, smoothnucz=2 ):
        if self.junchan!=self.nucchan:
            ut.show_info("Not in the same channel, no separation necessary")
            self.nucstain = np.copy(self.image[self.nucchan,])
            self.junstain = np.copy(self.image[self.junchan,])
            return
        from fish_feats.Separe import separateNucleiJunc, smoothNuclei
        ## Try to separate junction and nucleus that are in the same staining
        nucimage = np.copy(self.image[self.nucchan,])
        self.nucstain, self.junstain = separateNucleiJunc(nucimage, outrz=rmoutlier_radz, outrxy=rmoutlier_radxy, threshold=rmoutlier_threshold, edge=5, space=50, zhatrad=wth_radz, hatrad=wth_radxy)
        self.nucstain = smoothNuclei(self.nucstain, radxy=smoothnucxy, radz=smoothnucz)
    
    def separate_with_sepanet( self, model_dir ):
        from fish_feats.Separe import sepanet
        bothimage = np.copy(self.image[self.nucchan,])
        self.junstain, self.nucstain = sepanet( bothimage, model_dir )

    def should_separate( self ):
        if self.junchan==self.nucchan:
            ## both channels are absent
            if self.junchan is None:
                return False
            # separation has not been done yet
            if self.junstain is None:
                return True
        return False

    def check_separation(self):
        """ Check if should separate, do it if yes """
        if self.junchan==self.nucchan:
            # separation has not been done yet
            if self.junstain is None:
                self.separate_junctions_nuclei()
            return True
        return False
    
    def preprocess_junction_removebg(self, radius):
        """ Remove background in junction staining """
        if self.junstain is None:
            self.check_separation()
        from fish_feats.SegmentObj import preprocessRemoveBg
        radXY = radius
        radZ = floor(self.scaleZ/self.scaleXY*radius)
        self.junstain = preprocessRemoveBg(self.junstain, radXY, radZ)
    
    def preprocess_junction2D_removebg(self, img, radius):
        """ Remove background in projed junction staining """
        from fish_feats.SegmentObj import preprocessRemoveBg2D
        return preprocessRemoveBg2D(img, radius)
    
    def preprocess_junction2D_tophat(self, img, radius):
        """ Clean with top hat in junction staining """
        from fish_feats.Separe import topHat2D
        return topHat2D(img, radius)
    
    def preprocess_junction_tophat(self, radius):
        """ Clean with top hat in junction staining """
        if self.junstain is None:
            self.check_separation()
        from fish_feats.Separe import topHat
        radXY = radius
        self.junstain = topHat(self.junstain, radXY)

    def prepare_segmentation_junctions( self, projxy=40, projsmooth=3, do_clahe=True, clahe_grid=10 ):
        """ Check if should separate. Do local proj and normalize """
        if not self.check_separation():
            self.junstain = self.image[self.junchan,]

        start_time = time.time()
        projzo1 = local_max_proj( self.junstain, largexy=projxy, smooth=projsmooth )
        roijunc = prepJunctions( projzo1, do_clahe=do_clahe, clahe_grid=clahe_grid )
        if self.verbose:
            print("Local projection finished in {:.3f}".format((time.time()-start_time)/60)+" min")
        return roijunc
    
    def prepare_junctions(self):
        if self.junstain is None:
            self.check_separation()
    
    def do_segmentation_junctions( self, methodJunctions, roijunc, cell_diameter=20, chunking=1000 ):
        """ Junctions ZO1 segmentation """
        start_time = time.time()
        if methodJunctions == "Empty":
            self.junmask = np.zeros( self.get_image_shape(in2d=True), dtype="uint16" )
            return
        self.junmask = segmentJunctions( roijunc, methodJunctions, self.scaleXY, self.imagedir, self.imagename, diameter=cell_diameter, chunking=chunking, verbose=self.verbose ) 
        self.junmask[self.junmask==1] = np.max(self.junmask)+1 ## no label 1
        ut.show_info("Segmentation finished in {:.3f}".format((time.time()-start_time)/60)+" min")
    
   
    def get_tubeness_image(self, junc2d):
        from fish_feats.SegmentObj import image_tubeness
        return image_tubeness( junc2d )

    def measure_junctions_header(self):
        return self.pop.measureCellHeading()

    def measure_junctions(self):
        """ Measure the cells, keeping previous measures/features """
        if self.pop is None:
            self.popFromJunctions()

        results = self.pop.getResults( self.scaleXY, self.scaleZ )
        return results
    
    def get_cell_fromcoord( self, coord ):
        """ Get the cell label from coordinates """
        if self.pop is None:
            return None
        return self.pop.getCellFromCoord( coord )

    def popFromJunctions(self, proj=None, zpos=False ):
        """ create cells from the current masked image of junctions """
        #start_time = time.time()
        if self.pop is None:
            self.pop = Population(imageshape=self.imshape)

        if (self.junmask is None) or (self.junstain is None):
            ut.show_warning( "Mask was not loaded or junction and nuclei signals must be separated before")

        print("Creating cells from junctions")
    
        ## Load measures file if exists
        measurefile = self.get_filename( endname="_results.csv", ifexist=True )
        results = None
        hasz = False
        if measurefile != "":
            print( "Load previous results from file "+measurefile )
            results, hasz = self.load_results_file( measurefile )

        ## Calculates the Z position if necessary
        zmap = None
        if zpos and not hasz:
            if proj is None:
                projfilename = self.junction_projection_filename(ifexist=True)
                if projfilename != "":
                    proj = self.load_image(projfilename)
            if proj is not None:
                print("Calculating the z-map to place cells in 3D")
                zmap = self.calculate_zmap(proj, step_size=200, window_size=250)
       
        self.pop.createCellsFromMask(self.junmask, self.junstain, results, find_z=zpos, zmap = zmap, cells_direction=self.zdirection, talkative=self.verbose)
        ut.show_info("Created "+str(len(self.pop.cells))+" cells")
        return 1

    def cellsHaveZPos( self ):
        """ Check if the cells have Z position """
        if self.pop is None:
            return False
        return self.pop.cellsHaveZPos()

    def updateCellsZPos( self, step_size=100, window_size=150, save=False ):
        """ Calculate the zmap and replace the cells accordingly """
        proj = self.getJunctionsProjection()
        zmap = self.calculate_zmap(proj, step_size=step_size, window_size=window_size)
        self.pop.updateCellsZPosFromMap(zmap)
        if save:
            filename = self.get_filename( endname="_zmap.tif" )
            self.save_image( zmap, filename, hasZ=False, imtype="uint8" )
        
    def updateCellZPos(self, cell_label, zpos, img=None):
        """ Update the position of the given cell """
        self.pop.updateCellZPos(cell_label, zpos, img, self.scaleZ)

    def updateCellsZPosFromList(self, zlist):
        return None
    
    def hasCells(self):
        if self.pop is None:
            return False
        if self.junmask is None:
            return False
        if self.pop.imgcell is None:
            return False
        return True
    
    def nbCells(self):
        return len(self.pop.cells)
    
    def nbNuclei(self):
        return len(self.pop.nuclei)

    ################# Nuclei

    def nuclei_filename(self, ifexist=False):
        end = "_nuclei.tif"
        resfile = os.path.join(self.resdir, self.imagename+end)
        if ifexist:
            if not os.path.exists(resfile):
                return ""
        return resfile
    
    def load_segmentation_nuclei( self, filename, load_stain=True ):
        """ Load the results of nuclei segmentation from file"""
        self.nucmask, scaleXYm, scaleZm, names = ut.open_image(filename, verbose=self.verbose)
        if (self.nucmask.dtype == np.float32) or (self.nucmask.dtype == np.float64):
            self.nucmask = self.nucmask.astype(np.uint32)
        self.pop.setNucleiImage(self.nucmask)
        if load_stain and (self.nucstain is None):
            self.nucstain = self.image[self.nucchan,]
    
    def prepare_segmentation_nuclei( self ):
        if not self.check_separation():
            self.nucstain = self.image[self.nucchan,]
        else:
            if self.nucstain is None:
                self.separate_junctions_nuclei()

    def preprocess_nuclei_removebg(self, radius):
        if self.nucstain is None:
            self.prepare_segmentation_nuclei()
        from fish_feats.SegmentObj import preprocessRemoveBg
        radXY = radius
        radZ = floor(self.scaleZ/self.scaleXY*radius)
        self.nucstain = preprocessRemoveBg(self.nucstain, radXY, radZ)

    def prepare_nuclei(self):
        if self.nucstain is None:
            self.prepare_segmentation_nuclei()

    def preprocess_nuclei_median(self, radius):
        if self.nucstain is None:
            self.prepare_segmentation_nuclei()
        from fish_feats.SegmentObj import preprocessNucleiMedianFilter
        radXY = radius
        radZ = floor(self.scaleZ/self.scaleXY*radius)
        self.nucstain = preprocessNucleiMedianFilter(self.nucstain, radXY, radZ)
        
    # cellpose3D
    def do_segmentation_cellpose(self, diameter, threshold, resample=True, in3D=True, stitch_threshold=0.25, dask=False, chunk=1000 ):
        ut.show_info("Segmenting nuclei with CellPose3D")
        if self.model is None:
            from fish_feats.SegmentObj import initialize_cellpose
            self.model = initialize_cellpose()
        
        from fish_feats.SegmentObj import prepNuclei, getNuclei_cellpose3D
        treatedNuclei = prepNuclei(self.nucstain)  ## normalize the image
        treatedNuclei = np.expand_dims(treatedNuclei, axis=0)  ## add channel dimension
        self.nucmask = getNuclei_cellpose3D( self.model, treatedNuclei, 
                    diameter=diameter, 
                    scaleXY=self.scaleXY, scaleZ=self.scaleZ,
                    threshold=threshold,
                    flow_threshold=0.4,
                    resample=resample,
                    in3D=in3D,
                    stitch_threshold=stitch_threshold,
                    dask=dask,
                    chunk=chunk,
                    verbose=self.verbose )    
        self.nucmask[self.nucmask>0] = self.nucmask[self.nucmask>0] + 1
        if self.pop is not None:
            self.pop.setNucleiImage(self.nucmask)
    
    # stardist2D+association 3D
    def do_segmentation_stardist(self, threshold, overlap, assoMethod, associationlim, threshold_overlap):
        ut.show_info("Segmenting nuclei with Stardist2D+association3D")
        from fish_feats.SegmentObj import prepNuclei, getNuclei_stardist2DAsso3D
        treatedNuclei = prepNuclei(self.nucstain)  ## normalize the image
        self.nucmask = getNuclei_stardist2DAsso3D( treatedNuclei, self.scaleXY,
                            proba=threshold, 
                            overlap=overlap, 
                            assoMode = assoMethod,
                            assolim=associationlim,
                            threshold_overlap=threshold_overlap,
                            verbose=self.verbose )
        if self.nucmask is None:
            return
        self.nucmask[self.nucmask>0] = self.nucmask[self.nucmask>0] + 1
        if self.pop is not None:
            self.pop.setNucleiImage(self.nucmask)

    def get_segmented_nuclei(self):
        """ Mark points that are inside segmented nuclei """
        if self.pop is None:
            return None
        if self.pop.imgnuc is None:
            return None 
        return self.pop.imgnuc

    def hasNuclei(self):
        if self.pop is None:
            return False
        if self.pop.imgnuc is None:
            return False
        return True

    def filterNuclei( self, minimum_volume, keep_ifnz=2 ):
        if self.pop is None:
            self.pop = Population(imageshape=self.imshape)
        if self.pop.imgnuc is None:
            self.pop.imgnuc = self.nucmask
        self.pop.filterNuclei( minimum_volume, keep_ifnz, self.scaleXY*self.scaleXY*self.scaleZ, self.verbose )

    def popNucleiFromMask(self, associate=True):
        """ Load the nuclei and associate them to cells """
        self.pop.setNucleiImage(self.nucmask)
        self.pop.createNucleiFromMask( associate=associate, verbose=self.verbose, scaleXY=self.scaleXY, scaleZ=self.scaleZ )

    def measure_counts(self):
        rnachannels = [i for i in self.rnas.keys()]
        methods = [self.rnas[rnac].countName for rnac in rnachannels]
        self.pop.measureCellsCount( rnachannels, methods )

    def measure_count( self, rnachanel, method ):
        self.pop.measureCellsCount( [rnachanel], [method] )

    def get_counts( self ):
        """ Get the counts of the cells """
        if self.pop is None:
            return None
        return self.pop.getCounts()

    def get_measure_name(self, rnac):
        """ Return the name of the counting method of rna channel """
        return self.rnas[rnac].countName
    
    def image_count_from_table(self, countname):
        """ Create the image of cell RNA counts from current table """
        countimg = np.zeros(self.get_image_shape(in2d=True), np.uint16)
        self.pop.drawCountsInCells(countimg, countname)
        return countimg

    ### RNA hierarchical analysis

    def measure_onlycounts(self, rnachannels):
        methods = [self.rnas[rnac].countName for rnac in rnachannels]
        return self.pop.measureOnlyCellsCount(rnachannels, methods, self.scaleXY, self.scaleZ)

    def set_cells(self, clusterimg, clusters, celllabels):
        """ Put each cell value to its cluster """
        self.pop.drawCellsValues(clusterimg, clusters, celllabels)
    
    
    ###############  RNA

    def rna_filename(self, chan=0, how=".csv", ifexist=False):
        """ Default name of RNA files, can be an image or a csv """
        if how == ".tif":
            end = "_RNA"+str(chan)+".tif"
        elif how == ".csv":
            end = "_RNA"+str(chan)+".csv"
        return self.get_filename(end, ifexist)
    
    def load_rnafile( self, rnafilename, rnac, topop=True ):
        """ Load RNA spots for given channel from file """
        pop = None
        if topop:
            pop = self.pop
        rnaspot = RNASpots( rnac, verbose=self.verbose )
        self.rnas[rnac] = rnaspot
        ext = os.path.splitext(rnafilename)[1]
        # load from an image
        if ext == ".tif":
            rnaspots, scaleXYm, scaleZm, names = ut.open_image(rnafilename, verbose=self.verbose)
            rnaspot.update_spotsFromImage(rnaspots, methodName="Load", pop=pop)
        # load from a table file
        elif ext == ".csv":
            rnaspotDict = ut.load_dictlist(rnafilename, verbose=self.verbose)
            rnaspot.update_spotsFromDict(rnaspotDict, methodName="Load", pop=pop)
        ut.show_info("RNA spots loaded from file "+str(rnafilename))
    
    def get_rna_threshold(self, rnachan):
        if self.rnas.get(rnachan) is not None:
            if self.rnas[rnachan].threshold is None:
                return 0
            return self.rnas[rnachan].threshold
        return 0

    def find_rna(self, rnachan, spotZRadius, spotXYRadius, rmExtremeZ, threshold=None):
        if self.rnas.get(rnachan) is None:
            rnaspot = RNASpots(rnachan, verbose=self.verbose)
            self.rnas[rnachan] = rnaspot
        else:
            rnaspot = self.rnas[rnachan]
            rnaspot.reset_spots()
        rnaimg = self.image[rnachan,:,:,:]
        rnaspot.detect_spots_withbigfish(rnaimg, scaleZ=self.scaleZ, scaleXY=self.scaleXY, spotZRadius=spotZRadius, spotXYRadius=spotXYRadius, rmextr=rmExtremeZ, threshold=threshold)
    
    def find_rnas_in_image(self, rnaimg, chanlist, spotZRadius, spotXYRadius, threshold=None):
        chanlist = str(chanlist)
        if self.rnas.get(chanlist) is None:
            rnaspot = RNASpots(chanlist, verbose=self.verbose)
            self.rnas[chanlist] = rnaspot
        else:
            rnaspot = self.rnas[chanlist]
            rnaspot.reset_spots()
        rnaspot.detect_spots_withbigfish(rnaimg, scaleZ=self.scaleZ, scaleXY=self.scaleXY, spotZRadius=spotZRadius, spotXYRadius=spotXYRadius, rmextr=False, threshold=threshold)
        return rnaspot.get_points()

    def find_blobs_in_image(self, rnaimg, chanlist, minSigma, threshold):
        """ Detect 3D blobs (local maxima with DoG filtering) """
        chanlist = str(chanlist)
        if self.rnas.get(chanlist) is None:
            rnaspot = RNASpots(chanlist, verbose=self.verbose)
            self.rnas[chanlist] = rnaspot
        else:
            rnaspot = self.rnas[chanlist]
            rnaspot.reset_spots()
        rnaspot.detect_spots_withblobs(rnaimg, min_sigma=minSigma, threshold=threshold)
        return rnaspot.get_points()


    def assign_fromclosestrna(self, rnachan, method, limDist, nAbove, refrnas, nclosest):
        ut.show_info("Assign RNAs channel "+str(rnachan)+" with method "+method)
        rnaspot = self.rnas[rnachan]
        rnaclouds = [self.rnas[refrna] for refrna in refrnas]
        rnaspot.assign_fromcloud(self.pop, clouds=rnaclouds, 
                         scaleXY=self.scaleXY,
                         scaleZ=self.scaleZ,
                         distanceLimit=limDist, 
                         nclosest=nclosest,
                        method=method )

    def assign_rna(self, rnachan, method, limitDistAsso, nAbove):
        """ Assign the RNA spots to the cells with the defined parameters """
        angular_step = 4
        ut.show_info("Assign RNAs channel "+str(rnachan)+" with method "+method)
        if not self.hasCells():
            if method == "Projection" or method=="MixProjClosest" or method=="ClosestNucleus" or method== "Hull":
                ut.show_info("Cells not segmented yet, segment them before to use "+method+" method")
                return
        if method == "Hull" and self.pop.hullinited == 0:
            self.pop.initializeHull(angular_step)
        
        rnaspot = self.rnas[rnachan]
        rnaspot.assign_spots(self.pop, method=method,
                         distanceLimit=limitDistAsso, above=nAbove,
                         angular_step = angular_step,
                         scaleXY=self.scaleXY,
                         scaleZ=self.scaleZ)

    def draw_spots(self, spots, labels, chan):
        self.rnas[chan].update_spotsFromPoints(spots, labels, None)
        return self.rnas[chan].draw_spots3D(self.imshape, size=2)

    def save_spots(self, spots, props, chan, rnafile=None):
        """ Save the spots information to csv file """
        if rnafile is None:
            rnafile = self.rna_filename(chan=chan, how=".csv")
        ext = os.path.splitext(rnafile)[1]
        if ext == ".tif":
            imgspots = self.draw_spots( spots, props["label"], chan )
            self.save_image(imgspots, rnafile, hasZ=True )
            del imgspots
        if ext == ".csv":
            resdict = dict()
            resdict["X"] = spots[:,1]
            resdict["Y"] = spots[:,2]
            resdict["Z"] = spots[:,0]
            resdict["Label"] = props["label"]
            for propname, propval in props.items():
                if propname != "label":
                    resdict[propname] = propval
            ut.write_dict(rnafile, resdict)
        ut.show_info("RNA spots saved in file "+str(rnafile))

    def get_drawnspots(self, rnachan, size):
        imgoverlap = None
        rnaspot = self.rnas[rnachan]
        return rnaspot.draw_nonoverlap_spots3D(imgoverlap, self.imshape, size=size)

    def measure_spots(self, rnachan, measurechan=-1, measureimg=None, name=""):
        """ Measure intensity in the spots in the given channel """
        if measurechan >= 0:
            measureimg = self.image[measurechan]
            name = "C"+str(measurechan)
        if measureimg is None:
            ut.show_warning("No image or channel provided for measuring intensity")
            return None
        if name == "":
            name = str("Layer"+str(measurechan))
        self.rnas[rnachan].measure_spots_intensity( intensity_image = measureimg, name=name )
        return self.rnas[rnachan].measures[name]
    
    def threshold_spots_measure( self, rnachan, measure_name, threshold=0.5 ):
        """ Returns the measure if it exists """
        if self.rnas.get(rnachan) is None:
            print("RNA "+str(rnachan)+" not found")
            return None
        if self.rnas[rnachan].measures.get(measure_name) is None:
            print("Measure "+str(measure_name)+" not found for RNA "+str(rnachan))
            return None
        measures = self.rnas[rnachan].measures[measure_name]
        self.rnas[rnachan].measures[measure_name] = np.greater_equal(measures, threshold).astype(float).tolist()


    def get_spots_measure( self, rnachan, measure_name ):
        """ Returns the measure if it exists """
        if self.rnas.get(rnachan) is None:
            print("RNA "+str(rnachan)+" not found")
            return None
        if self.rnas[rnachan].measures.get(measure_name) is None:
            print("Measure "+str(measure_name)+" not found for RNA "+str(rnachan))
            return None
        return self.rnas[rnachan].measures[measure_name]

    def get_spots(self, rnachan):
        return self.rnas[rnachan].get_pointswithprops()

    def set_spots(self, rnachan, spots):
        self.rnas[rnachan].set_points(spots)
    
    def update_spotsAndCountFromPoints(self, spots, labels, scores, chan):
        self.rnas[chan].update_spotsFromPoints(spots, labels, scores, self.pop)
    
    def get_rnalist(self):
        return [i for i in self.rnas.keys()]
    
    def get_done_rnalist(self):
        res = []
        for i, rna in self.rnas.items():
            if len(np.unique(rna.labels)) > 1:
                res.append(i)
        return res

    def get_overlapping_channels( self, channel ):
        """ Find saved overlapping RNASpots that contained the current channel """
        
        ## Check if overlapping spots already in the list of loaded RNAs
        for rnachan in self.rnas.keys():
            if isinstance(rnachan, list):
                ## if the channel has been searched for overlapping points
                if channel in rnachan:
                    return rnachan
        
        ## Otherwise check if a file exists with the correct name containing over RNA
        rnafile = os.path.join(self.resdir, self.imagename+"_RNA_over_")
        saved_files = ut.get_filelist(rnafile+"*.csv")
        for fullfile in saved_files:
            cfile = os.path.basename(fullfile)
            rna_nums = cfile.split("_RNA_over_")
            rna_nums = rna_nums[1]
            rna_nums = rna_nums[0:len(rna_nums)-4]
            for num in list(rna_nums):
                if num.isdigit() and int(num) == channel:
                    self.load_rnafile( fullfile, rna_nums )
                    return rna_nums
        return None

    def find_spot(self, channel, spot, distance=0.2):
        """ Check if RNASpot of channel contains a spot within distance of spot """
        if channel not in self.rnas.keys():
            return False
        return (self.rnas[channel].find_spot( spot, self.scaleXY, self.scaleZ, distance )>= 0 )

    def mixchannels(self, chanlist):
        """ Normalize and add the channels """
        img = np.zeros(self.get_image_shape(in2d=False), np.float16)
        img = img + 1
        #one_max = floor(255/len(chanlist))
        for chan in chanlist:
            norm_image = ut.normalize_img(self.get_channel(chan))
            img = img * norm_image
        #img[img<(one_max*(0.25+len(chanlist)/2.0))] = 0
        #img[img<one_max] = img[img<one_max]*0.25
        img = adjust_gamma(img, 2)
        return img

    def associateCN(self, nucleus, cell):
        self.pop.associateCNLabels(nucleus, cell)
        self.nucmask = self.pop.imgnuc

    def go_association( self, distance, pbar=None ):
        ut.show_info("Start doing association...")
        if pbar is not None:
            pbar.total = 2
        if len(self.pop.nuclei) <= 0:
            self.pop.createNucleiFromMask(associate=False, verbose=self.verbose, scaleXY=self.scaleXY, scaleZ=self.scaleZ)
        if pbar is not None:
            pbar.update(1)
        self.pop.associateCellsNuclei( association_limit=distance, scaleXY=self.scaleXY, scaleZ=self.scaleZ, verbose=self.verbose, pbar=pbar)
        #self.pop.relabelNuclei()
        self.nucmask = self.pop.imgnuc

    def getAverageCellZ(self):
        meanz = self.pop.getMeanCellsZ()
        return int(meanz)

    def measure_nuclear_intensity( self, channel ):
        """ Measure intensity in segmented nuclei """
        img = self.image[channel]
        results = self.pop.measureNuclearStaining( img, channel )
        return results

    def measureCytoplasmic(self, cytochannels, bgrois, zthickness):
        """ Measure background mean intensity (in the ROI) """
        start_time = time.time()
        meanz = bgrois[0][0][0][0]
        until = meanz + self.zdirection*zthickness
        dbg = min(meanz, until)
        ubg = max(meanz, until)
        dbg = max(dbg, 0)
        ubg = min(ubg, self.imshape[0])
        meanbgints = []
        ut.show_info("Measuring cytoplasmic signals in channels: "+str(cytochannels))
        for cyt, bgroi in zip(cytochannels, bgrois):
            bgroi = bgroi[0]
            cmean = np.mean( self.image[cyt, int(dbg):int(ubg+1),int(bgroi[0][1]):int(bgroi[3][1]), int(bgroi[0][2]):int(bgroi[1][2])] )
            meanbgints.append( cmean )

        results = self.pop.measureCellsCytoplasmic( cytoThickness=zthickness, cytochannels=cytochannels, imagesCyto=self.image, meanbgints=meanbgints, scaleXY=self.scaleXY, scaleZ=self.scaleZ )
        print("Cytoplasmic measures in {:.3f}".format((time.time()-start_time)/60)+" min")
        return results

    def drawCytoplasmicMeasure(self, cytochan, results):
        """ Draw intensity image of the cytoplasmic measure in each cell """
        column = "Cyto"+str(cytochan)+"_MeanNormalisedIntensity"
        proj = self.pop.drawProjectedCyto( results, column )
        return proj 

    def fillFeature(self, featname, value):
        self.pop.fill_measure(featname, value)

    def features_filename(self, ifexist=True):
        """ Default filename of features file """
        filename = self.get_filename(endname="_features.csv", ifexist=ifexist)
        return filename

    def image_feature_from_table(self, featname):
        """ Create the classified feature image from current table """
        featimg = np.zeros(self.get_image_shape(in2d=True), np.uint8)
        self.pop.drawFeatureInCells(featimg, featname)
        return featimg


    def loadFeatureFromImage(self, featname):
        endname = "_feat_"+featname+".tif"
        featimg = self.load_image(self.build_filename(endname))
        self.pop.loadFeature(featname, featimg)
        return featimg

    def loadFeaturesTable(self, endname):
        """ Load all features already measured and saved in the given file, previous version with separated features file """
        featfile = os.path.join(self.resdir, self.imagename+endname)
        if os.path.exists(featfile):
            with open(featfile, 'r') as infile:
                csvreader = csv.DictReader(infile)
                for row in csvreader:
                    self.pop.addFeatureValue(row)
                print("Loaded previous features value in the table: "+str(row.keys()))

    def loadFeatureFile(self, featfile):
        """ Load feature(s) from image/table file """
        if not os.path.exists(featfile):
            print("File "+featfile+" not found")
            return
        filename, filext = os.path.splitext(featfile)
        if filext==".tif":
            featname = filename.split("_feat_")[1]
            featimg = self.load_image(featfile)
            self.pop.loadFeature(featname, featimg)
        if filext==".csv":
            self.loadFeatureTable(featfile)

    def loadCytoplasmicTable( self, cytofile ):
        """ Load all cytoplasmic measures already done from the given file """
        if os.path.exists(cytofile):
            with open(cytofile, 'r') as infile:
                csvreader = csv.DictReader( infile )
                for row in csvreader:
                    self.pop.addCytoplasmicValue(row)
                print("Loaded previous cytoplasmic value in the table")
    
    def loadFeatureTable(self, featfile):
        """ Load all features already measured and saved in the given file """
        if os.path.exists(featfile):
            with open(featfile, 'r') as infile:
                csvreader = csv.DictReader(infile)
                for row in csvreader:
                    self.pop.addFeatureValue(row)
                print("Loaded previous features value in the table: "+str(row.keys()))

    def getFeaturesTable(self):
        return self.pop.getFeaturesTable()

    def getFeaturesList(self):
        """ Get the list of current features """
        featlist = self.pop.getFeaturesHeading()
        return featlist

    def getFeatureMax(self, featname):
        """ Returns the max value of featname measures if found, else None """
        return self.pop.getMaxFeature(featname)

    def classifyCells(self, featname, projchan, threshold_mean, threshold_fill):
        """ Perform initial classification based on thresholding """
        projimg = np.mean(self.image[projchan], axis=0)
        return self.pop.classifyCellsFromThreshold( featname, projimg, threshold_mean, threshold_fill )

    def classifyBoundaryCells( self, featname, border=0, boundary=2 ):
        """ Classify cells if they are on edge/boundary of the tissue """
        return self.pop.classifyCellsFromBoundaries( featname, border, boundary )

    def update_cell_feature(self, featname, celllabel, newvalue ):
        self.pop.putFeatureCellValue(featname, celllabel, newvalue)
    
    def change_cell_feature(self, featname, celllabel, newvalue, featimg ):
        """ Update the value of cell and redraw it """
        self.pop.changeFeatureCellValue( featname, celllabel, newvalue, featimg )
    
    def get_feature_value(self, featname, celllabel):
        res = self.pop.getFeatureCellValue(featname, celllabel)
        if res is None:
            return 0
        return res
    
    def tryHull(self):
        return self.pop.drawCellsHull()

    def tryTogether(self):
        return self.pop.tryCell()

    def calculate_zmap(self, projimg, step_size, window_size):
        """ Calculate the zmap of the cells position based on the projection """
        if self.junstain is None:
            self.check_separation()
            if self.junstain is None:
                ut.show_warning("Load junction staining (separated if necessary) before")
                return
        zmap = np.zeros(projimg.shape, "uint8")
        for i, x in enumerate(range(0, projimg.shape[0], step_size)):
            zmap_cur = process_x( x, step=step_size, projimg=projimg, img=self.junstain, winsize=window_size )
            zmap[x:(x+step_size),:] = zmap_cur
        return zmap

    def tryDiffusion( self, nchan ):
        """ Test drawing cells by diffusive walk """
        from skimage.segmentation import random_walker
        labels = self.getJunctionsImage3D()
        cimg = self.image[nchan]
        print("drawing done")
        diffused = random_walker( cimg, labels, beta=100, tol=0.5 )
        return diffused


