import numpy as np
from math import floor, pow, sqrt
from scipy.ndimage import measurements, label
from scipy.ndimage import mean as ndmean
from cv2 import circle

try:
    import bigfish.detection as detection
except ImportError:
    print("Import of bigfish module failed")

class RNASpots:

    """
        Handle the RNA spots: segment and assign to cells
        One RNA spots population corresponds to the RNA segmented in one color channel
    """

    def __init__(self, channel=1, verbose=True):
        self.channel = channel
        self.verbose = True
        self.spots = None
        self.unassigned = 1
        self.threshold = None
        self.labels = []       ## spot label = Cell label it's assigned to
        self.scores = []       ## score = estimated confidence of the assignement
        self.overlap = []
        self.countName = ""  #" method used for the assignement
        self.measure_radius = 4  ## measure intensity in a radius of 4 pixels around/inside the spot
        self.measures = {}    ## measures done

    def reset_spots(self):
        self.spots = None
        self.labels = []
        self.scores = []
        self.overlap = []
        self.measures = {}    ## measures done

    def set_points(self, spots):
        """ Set the spots collection from the spots list """
        self.reset_spots()
        self.spots = spots
        self.labels = list(np.repeat(1, len(self.spots)))
        self.scores = [0]*len(self.labels)
        #print("Set points, what score?")

    def nspots(self):
        """ Number of RNA spots in the collection """         
        if self.spots is not None:
            return len(self.spots)
        return 0

    def detect_spots_withbigfish(self, img, scaleZ, scaleXY, spotZRadius, spotXYRadius, rmextr=True, threshold=None):
        """ Detect RNA spots with big-fish """
        from fish_feats.Separe import topHat
        from fish_feats.SegmentObj import normalizeQuantile
        img = topHat(img, xyrad=floor(30*scaleXY))
        img = normalizeQuantile(img, qmin=0.001, qmax=0.999, vmax=255)
        # detect with big-Fish: spots sizes are to be put in nanometers
        spots, self.threshold = detection.detect_spots(
                images = img,
                threshold = threshold,
                return_threshold = True,
                voxel_size = (int(scaleZ*1000), int(scaleXY*1000), int(scaleXY*1000)),
                spot_radius = (spotZRadius, spotXYRadius, spotXYRadius)
                )
        if rmextr:
            self.spots = []
            for spot in spots:
                if (spot[0,] > 0) and (spot[0,] < (img.shape[0]-1)):
                        self.spots.append(spot)
        else:
            self.spots = spots

        self.labels = list(np.repeat(1, len(self.spots)))
        self.scores = [0]*len(self.labels)
        #self.overlap = list(np.repeat(-1, len(self.spots)))

        if self.verbose:
            print("    Detected spots with Big-Fish: ")
            print("    \t nb spots: {0}".format(len(self.spots)))
            print("    \t threshold: {0}".format(self.threshold))
    
    def detect_spots_withblobs(self, img, min_sigma, threshold=None):
        """ Detect RNA spots as blobs """
        # detect with blob detector: do DoG filtering and local max
        from skimage.feature import blob_dog
        spots = blob_dog(img, min_sigma=min_sigma, max_sigma=min_sigma*10, threshold=threshold, overlap=0.25, exclude_border=True)
        
        self.spots = spots[:,0:3]
        self.labels = list(np.repeat(1, len(self.spots)))
        self.scores = [0]*len(self.labels)

        if self.verbose:
            print("    Detected spots as blob: ")
            print("    \t nb spots: {0}".format(len(self.spots)))


    def draw_spots2D(self, imgshape, val=1):
        imgspots = np.zeros(imgshape, dtype=np.uint16)
        for spot in self.spots:
            imgspots[spot[1], spot[2]] += val
        return imgspots
    
    def drawPoint(self, img, pt, col=255, rad=1):
        """ Draw one RNA spot in the image """
        if len(pt)<=2:
            img = circle(img, (pt[1], pt[0]), radius=rad, color=col, thickness=-1)
        else:
            img[pt[0]] = circle(img[pt[0]], (pt[2], pt[1]), radius=rad, color=col, thickness=-1)

    def draw_spots3D(self, imgshape, size=1):
        imgspots = np.zeros(imgshape, dtype=np.uint16)

        for spot, label in zip(self.spots, self.labels):
            if label < 0:
                lab = int(self.unassigned)
            else:
                lab = int(label)
            self.drawPoint(imgspots, spot, col=lab, rad=size)
        return imgspots
    
    def draw_nonoverlap_spots3D(self, imgover, imgshape, size=1):
        """ Create image of spots that do not overlap, with their corresponding labels """
        imgspots = np.zeros(imgshape, dtype=np.uint16)

        for spot, label, overlap in zip(self.spots, self.labels, self.overlap):
            if imgover is None or overlap == -1: 
                if label < 0:
                    lab = int(self.unassigned)
                else:
                    lab = int(label)
                self.drawPoint(imgspots, spot, col=lab, rad=size)
            else:
                if imgover is not None:
                    self.drawPoint(imgover, spot, col=overlap, rad=size*2)

        return imgspots
    
    def get_points(self):
        """ return coordinates of all the spots """
        return self.spots

    def get_pointswithlabels(self):
        """ return coordinates and labels of all the spots """
        return self.spots, self.labels
    
    def get_pointswithprops(self):
        """ return coordinates and labels of all the spots """
        return self.spots, self.labels, self.scores

    def measure_spots_intensity(self, intensity_image, name):
        """ Measure the mean intensity of all points in the image """
        self.measures[name] = []
        for spot in self.spots:
            if len(spot)>2:
                ## take few pixels around spot center
                minr = [0, 0]
                maxr = [0, 0]
                for i in range(2):
                    minr[i] = max(spot[i+1]-self.measure_radius, 0)
                    maxr[i] = min(spot[i+1]+self.measure_radius, intensity_image.shape[i+1])
                mint = np.mean( intensity_image[spot[0], minr[0]:maxr[0], minr[1]:maxr[1]] )
            else:
                ## take few pixels around spot center
                minr = [0, 0]
                maxr = [0, 0]
                for i in range(2):
                    minr[i] = max(spot[i]-self.measure_radius, 0)
                    maxr[i] = min(spot[i]+self.measure_radius, intensity_image.shape[i])
                mint = np.mean( intensity_image[minr[0]:maxr[0], minr[1]:maxr[1]] )
            self.measures[name].append(mint)

    def distance(self, spa, spb, scaleXY, scaleZ):
        """ distance between two spots """
        return sqrt( pow((spa[0]-spb[0])*scaleZ, 2) + pow((spa[1]-spb[1])*scaleXY,2) + pow((spa[2]-spb[2])*scaleXY,2) )
    
    def average(self, spa, spb):
        """ average between two spots """
        sp = np.copy(spa)
        for i in range(len(spa)):
            sp[i] = int((spa[i]+spb[i])/2)
        return sp
    
    def get_nclosests(self, inspot, scaleXY, scaleZ, distlim, nclosest, lclosest=[], dclosest=[]):
        """ Find if the nclosest points from inspot, within dist """
        for i in range(len(lclosest), nclosest):
            dclosest.append(distlim*2)  ## croissant et > dist
            lclosest.append(-1)
        
        for j, jspot in enumerate(self.spots):
            dx = abs(jspot[2]-inspot[2])*scaleXY
            if dx < distlim:
                dy = abs(jspot[1]-inspot[1])*scaleXY
                if dy < distlim:
                    dz = abs(jspot[0]-inspot[0])*scaleZ
                    if dz < distlim:
                        dist = sqrt(dz*dz*+dy*dy+dx*dx)
                        if dist < distlim:
                            cind = 0
                            while cind<nclosest and dist > dclosest[cind]:
                                cind = cind + 1
                            ind = self.labels[j]
                            while cind < nclosest:
                                tmp = dclosest[cind]
                                tmpind = lclosest[cind]
                                dclosest[cind] = dist
                                lclosest[cind] = ind
                                dist = tmp
                                ind = tmpind
                                cind = cind + 1
        return lclosest, dclosest

    def find_spot(self, inspot, scaleXY, scaleZ, dist):
        """ Find if there is a spot within distance dist of spot """
        for j, jspot in enumerate(self.spots):
            dx = abs(jspot[2]-inspot[2])*scaleXY
            if dx < dist:
                dy = abs(jspot[1]-inspot[1])*scaleXY
                if dy < dist:
                    dz = abs(jspot[0]-inspot[0])*scaleZ
                    if dz < dist:
                        if sqrt(dz*dz+dy*dy+dx*dx) < dist:
                            return j
        return -1

    def list_overlap_spots(self, cospots, scaleXY, scaleZ, dist=0.1):
        over = []
        for i, spot in enumerate(self.spots):
            j = cospots.find_spot(spot, scaleXY, scaleZ, dist)
            # found a spot at the same position
            if j != -1:
                over.append([i,j])
        return over
    
    def overlap_spots(self, otherspots, noverlap, ind, indother, scaleXY, scaleZ, dist=0.1):
        """ Compare to RNASpot for overlapping spots """
        for i, spot in enumerate(self.spots):
            j = otherspots.find_spot(spot, scaleXY, scaleZ, dist)
            
            # found a spot at the same position
            if j != -1:
                # one of the spot has already been assigned in an overlap
                if self.overlap[i] >= 0 or otherspots.overlap[j] >= 0:
                    self.overlap[i] = max(self.overlap[i], otherspots.overlap[j])
                    otherspots.overlap[j] = self.overlap[i]
                else:
                    self.overlap[i] = noverlap
                    otherspots.overlap[j] = noverlap
                    noverlap += 1
        
        return noverlap

    def kept_fromoverlap(self, keptspots, rnaimg, pop, method="Projection", distanceLimit=50, above=1, size=1, angular_step=0):
        for spot, over in zip(self.spots, self.labels):
            pt = (int(spot[0]), int(spot[1]), int(spot[2]))
            if keptspots[pt] > 0:
                icell, dist, score = self.assign_onespot( pop, spot, method=method, distanceLim=distanceLimit, above=above, angular_step=angular_step )   ## add the spot to the corresponding cell
                if icell > 0:
                    lab = pop.labels["Cell_"+str(icell)]
                self.drawPoint(rnaimg, spot, col=lab, rad=size)

    def update_spotsFromPoints(self, spots, labels, scores, pop=None):
        """ Load all the spots from the given points coordinates and labels """
        self.reset_spots()
        self.labels = labels.astype(int)
        self.spots = spots.astype(int)
        self.scores = scores.astype(float)
        countName = self.countName

        if pop is not None:
            pop.resetCellCounts(countName)
        
            for lab in self.labels:
                j, cell = pop.findCellWithLabel(lab)
                if j != -1:
                    cell.addCount(countName, 1)

    def update_spotsFromDict( self, spotdict, methodName="", pop=None):
        """ Load all the spots from the given dict """
        self.countName = "nbRNA_C"+str(self.channel)+"_"+methodName
        self.spots = []
        self.labels = []
        self.scores = []
        if pop is not None:
            pop.resetCellCounts(self.countName)
        
        for row in spotdict:
            self.spots.append( [int(float(row["Z"])), int(float(row["X"])), int(float(row["Y"]))] )
            lab = int(float(row["Label"])) 
            self.labels.append(lab)
            ## compatibility to older saved files, don't have the score column
            if "Score" in row:
                score = int(float(row["Score"])) 
            else:
                score = 0
            self.scores.append(score)
            if pop is not None:
                j, cell = pop.findCellWithLabel(lab)
                if j != -1:
                    cell.addCount(self.countName, 1)

    def update_spotsFromImage(self, img, methodName="", pop=None):
        """ Read a labelled RNA spots image (pixel value=cell label), old version """
        self.countName = "nbRNA_C"+str(self.channel)+"_"+methodName
        points, nf = label(img)
        if np.sum(points[points!=0]) <= 0:
            self.spots = []
            print( "Warning, no spots found in rna image "+str(self.channel) )
            return
        lpoints = np.unique(points[points!=0])
        
        coords = measurements.center_of_mass(points, labels=points, index=lpoints)
        self.labels = ndmean(img, points, lpoints)
        labels = self.labels.copy()
        self.scores = [0]*len(self.labels)
        
        self.spots = []
        if pop is not None:
            pop.resetCellCounts(self.countName)
        
        for pt, lab, cind in zip(coords, labels, range(len(self.labels))):
            self.spots.append([int(pt[0]), int(pt[1]), int(pt[2])] )
            if not isinstance(lab, int):
                lab = int(lab)
            if lab == self.unassigned:
                self.labels[cind] = -1
            else:
                if pop is not None:
                    j, cell = pop.findCellWithLabel(lab)
                    if j != -1:
                        pop.cells[j].addCount(self.countName, 1)
                    else:
                        self.labels[cind] = -1
                
    
    def assign_spots(self, pop, method="Projection", distanceLimit=15, above=1, angular_step=0, scaleXY=1, scaleZ=1):
        self.countName = "nbRNA_C"+str(self.channel)+"_"+method
        pop.resetCellCounts( self.countName, zero=True )

        for i, spot in enumerate(self.spots):
            cell, dist, score = pop.assign_onespot( spot, method=method, distanceLim=distanceLimit, above=above, angular_step=angular_step, nchannel=self.channel, countName = self.countName, scaleXY=scaleXY, scaleZ=scaleZ, prejuge=-1 )
            if cell is not None:
                self.labels[i] = cell.label
                self.scores[i] = score
            else: 
                self.labels[i] = -1  ## no cell.
                self.scores[i] = 0
    
    def assignSpotToCell( self, pop, ispot, icell, method ):
        if icell > 0:
            self.labels[ispot] = pop.cells[icell].label
            pop.cells[icell].addCount(self.countName,1)
        else: 
            self.labels[ispot] = -1  ## no cell.

    def assign_from_volume( self, pop, imgVol, method ):
        self.countName = "nbRNA_C"+str(self.channel)+"_"+method
        pop.resetCellCounts( self.countName )
        for i, spot in enumerate(self.spots):
            icell = imgVol[spot[0], spot[1], spot[2]]
            self.assignSpotToCell( pop, i, icell, method )

    def assign_fromcloud(self, pop, clouds, scaleXY, scaleZ, distanceLimit=15, nclosest=5, method="ClosestPoints"):
        self.countName = "nbRNA_C"+str(self.channel)+"_"+method
        pop.resetCellCounts( self.countName )
        for i, spot in enumerate(self.spots):
            labcell, dist = self.fromClosestCloud(spot, clouds, method=method, distanceLim=distanceLimit, scaleXY=scaleXY, scaleZ=scaleZ, nclosest=nclosest)
            icell, cell = pop.findCellWithLabel(labcell)
            self.assignSpotToCell( pop, i, icell, method )
    
    def fromClosestCloud(self, pt, clouds, method, distanceLim, scaleXY, scaleZ, nclosest):
        """ assign rna from cloud of points """
        list_closest = []
        dist_closest = []
        for cloud in clouds:
            list_closest, dist_closest = cloud.get_nclosests(pt, scaleXY, scaleZ, distanceLim, nclosest, list_closest, dist_closest)

        closest = [ clos for clos, dclos in zip(list_closest, dist_closest) if dclos < distanceLim ]
        if len(closest) > 0:
            pcell = max(closest, key=closest.count)
        else:
            pcell = -1
        return (int(pcell), min(dist_closest))
