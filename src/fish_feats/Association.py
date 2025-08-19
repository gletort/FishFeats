## Associate contours and nuclei by distance 
## algorithm hongrois: Kuhn-Munkres
import numpy as np
from math import sqrt, floor
from scipy.ndimage.morphology import distance_transform_edt
from munkres import Munkres
from skimage.measure import label, regionprops

def distance2DCenters( cent0, cent1, scaleXY ):
    if cent0 is None:
        return 0
    return sqrt( (cent0[0]-cent1[0])*(cent0[0]-cent1[0]) + (cent0[1]-cent1[1])*(cent0[1]-cent1[1]) )*scaleXY

def associateWindows(wlab, wbal, dlim, scaleXY):
    labels = np.unique(wlab[wlab>0])
    balels = np.unique(wbal[wbal>0])
    nbal = len(balels)
    nlab = len(labels)
    resbal = np.zeros_like(wbal)
    n = max(nbal, nlab)
    matrix = np.zeros((n, n))  ## should be square. 
    if n == 0:
        return resbal

    ## distance_transform is distance to closest background, so inverse
    dist2lab, nearest_coord = distance_transform_edt(wlab==0, return_indices=True)
    dillabels = np.zeros_like(wlab)
    ## check if within reasonnable distance
    dilate_mask = ((dist2lab*scaleXY*scaleXY) <= dlim)
    masked_nearest_label_coords = [ dind[dilate_mask] for dind in nearest_coord]
    nearest_labels = wlab[tuple(masked_nearest_label_coords)]
    dillabels[dilate_mask] = nearest_labels

    ## look for best fit
    for j, jlab in enumerate(balels):
        nei = dillabels[wbal==jlab]
        for i, ilab in enumerate(labels):
                count = np.sum(nei==ilab)
                if count > 0:
                    matrix[i][j] = 1.0/(count+1)
                else:
                    matrix[i][j] = dlim+1
    
    ## algorithm hongrois: Kuhn-Munkres
    dmat = np.copy(matrix)
    munk = Munkres()
    assoc = munk.compute(matrix)
    matrix = None
    munk = None
    for asso in assoc:
        if asso[0]<nlab and asso[1]<nbal:
            if (dmat[asso[0]][asso[1]] > 0) and (dmat[asso[0]][asso[1]]<dlim):
                ## associate
                resbal[wbal==balels[asso[1]]] = labels[asso[0]]

    return resbal
    
def associateLabWithLab(lab, bal, dlim, scaleXY):
    """ associate labels of img 2 to labels of img 1 """
    ##### do overlapping windows otherwise calcul distances too slow (to test)
    sizex = 1000
    sizey = 1000
    over = 50
    sizes = lab.shape

    posy = 0
    resbal = np.zeros(bal.shape, dtype="uint16")
    while posy < sizes[0]:
        posx = 0
        while posx < sizes[1]:
            windowbal = np.copy(bal[posy:(posy+sizey),posx:(posx+sizex)])
            windowlab = lab[posy:(posy+sizey),posx:(posx+sizex)]
            assobal = associateWindows( windowlab, windowbal, dlim, scaleXY )
            bal[posy:(posy+sizey),posx:(posx+sizex)][assobal>0] = 0
            resbal[posy:(posy+sizey),posx:(posx+sizex)][assobal>0] = assobal[assobal>0]
                
            posx += (sizex-over)        
        posy += (sizey-over)

    ## what is left in bal image has not been associated, add it to the result image as new label
    maxlab = np.max(lab)
    for l in np.unique(bal):
        if l > 0:
            resbal[bal==l] = maxlab+1
            maxlab = np.max(resbal)
 
    return resbal     

def associateNucleus(labs, dlimit=3, scaleXY=1):
    """ Associate each slice with previous slice """
    for i in range(len(labs)):
        if i > 1:
            rlab = associateLabWithLab( labs[i-1,], labs[i,], dlimit, scaleXY )
            labs[i,] = rlab
    return labs

def associateOverlap( labimg, labimgprev, threshold_overlap=0.25):
    nuclei_prop = regionprops( labimg, intensity_image=labimgprev )
    new_label = np.max(labimgprev) + 1
    #taken = []
    for nucprop in nuclei_prop:
        overlap = nucprop.image_intensity
        overlabs, counts = np.unique(overlap, return_counts=True)
        if 0 in overlabs:
            zero = np.where(overlabs==0)
            zero = zero[0]
            overlabs = [over for i, over in enumerate(overlabs) if i != zero]
            counts = [over for i, over in enumerate(counts) if i != zero]
        
        done = False
        if len(counts)>0:
            maxlabind = np.argmax( counts )
            #maxlabind = maxlabind[0]
            if counts[maxlabind]/nucprop.area > threshold_overlap:
                ## overlap between the two labels, associate
                labimg[nucprop.bbox[0]:nucprop.bbox[2], nucprop.bbox[1]:nucprop.bbox[3]][nucprop.image] = overlabs[maxlabind]
                done = True

        if not done:
            # no match found, new label
            labimg[nucprop.bbox[0]:nucprop.bbox[2], nucprop.bbox[1]:nucprop.bbox[3]][nucprop.image] = new_label
            new_label = new_label + 1
            #taken.append(maxlabind)
    return labimg


def associateNucleusOverlap(labs, threshold_overlap):
    """ Associate each slice with previous slice based on IOU """
    for i, lab in enumerate(labs):
        if i >= 1:
            plab = associateOverlap( lab, plab, threshold_overlap )
        else:
            # first slice
            plab = lab
        labs[i,] = plab
    return labs 


def associate_objects(pop, wnuc, wcells, dlim, scaleXY, scaleZ):
    ## algorithm hongrois: Kuhn-Munkres
    ncells = len(wcells)
    nnuclei = len(wnuc)
    n = max(ncells, nnuclei)
    #print(str(ncells)+" "+str(nnuclei)+" "+str(n))

    matrix = np.zeros((n,n))  ## should be square.
    row = 0
    for i, cell in enumerate(wcells):
        for j, nuc in enumerate(wnuc):
            matrix[i][j] = pop.distanceNucleusToCell( nuc, cell, scaleXY, scaleZ )  ## put more weights to XY distance than z

    munk = Munkres()
    dmat = np.copy(matrix)
    assoc = munk.compute(matrix)
    munk = None
    associated = []
    associatedNuc = []
    #acells = []
    ## assoc contient indices. If indices > nnuclei or ncells, mean non associated
    for asso in assoc:
        if asso[0] < ncells and asso[1] < nnuclei:
            if dmat[asso[0]][asso[1]] < dlim:
                ## associate them
                pop.associateNucleusAndRelabel( nucleus=wnuc[asso[1]], cell=wcells[asso[0]] )
                associated.append(asso[0])
                associatedNuc.append(asso[1])
       
    dmat = None
    return associated, associatedNuc   

        
def associate_nucleiToCell(pop, imgsizes, dlim=20, scaleXY=1, scaleZ=1, pbar=None):
    """ Need scaling for non isotropic distances """
    ##### do overlapping windows otherwise association too slow (too big matrix)
    sizex = floor(180/scaleXY)
    sizey = floor(180/scaleXY)
    over = floor(40/scaleXY)
    margin = floor(5/scaleXY)

    posy = 0
    #fullcells = []  ## cells with associated nuclei
    nuclei = pop.nuclei.values()
    cells = pop.cells.values()
    if pbar is not None:
        pbar.total = imgsizes[0]
    while posy < imgsizes[0]:
        if pbar is not None:
            pbar.update(posy)
        posx = 0
        while posx < imgsizes[1]:
            border = (posy, posx, posy+sizey, posx+sizex)
            
            winuclei = []
            leftnuclei = []
            #print("newcnts "+str(len(newcnts)))
            for nuc in nuclei:
                    if nuc.insideBorderCenter(border):
                        winuclei.append(nuc)
                    else:
                        leftnuclei.append(nuc)
            nuclei = leftnuclei
            
            wincells = []
            border = (posy-margin, posx-margin, posy+sizey+margin, posx+sizex+margin)
            leftcells = []
            for cell in cells:
                    if cell.insideBorderCenter(border):
                        wincells.append(cell)
                    else:
                        leftcells.append(cell)
            
            if len(winuclei)>0 and len(wincells)>0:
                associated, associatedNuc = associate_objects(pop, winuclei, wincells, dlim, scaleXY, scaleZ)
                #fullcells = fullcells + acells
                
                for i in range(len(wincells)):
                    if i not in associated:
                        leftcells.append(wincells[i])
                
                for i in range(len(winuclei)):
                    if i not in associatedNuc:
                        nuclei.append(winuclei[i])
                        
            cells = leftcells
                
            posx += (sizex-over)        
        posy += (sizey-over)
 
    print("Unassociated nuclei left "+str(len(nuclei)))
    pop.relabelUnassociatedNuclei(nuclei)
