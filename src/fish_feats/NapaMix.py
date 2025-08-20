import fish_feats.Utils as ut
import fish_feats.FishWidgets as fwid
import numpy as np
import os
from qtpy.QtWidgets import QVBoxLayout, QWidget 


class CropImage( QWidget ):
    """ Crop the image and the associated files """
    
    def __init__( self, viewer, mig, cfg ):
        """ Interface to crop the image and the associated files """

        self.viewer = viewer
        self.mig = mig
        self.cfg = cfg
        self.crop_layer = None

        self.add_shape_layer()

        super().__init__()
        layout = QVBoxLayout()

        ## get the name of the output crop
        line_crop, self.crop_name = fwid.value_line( "Cropped name:", self.mig.crop_name(), descr="Choose the name of the output cropped image" )
        layout.addLayout( line_crop )

        ## button to launch the crop
        crop_btn = fwid.add_button( "Do crop", self.go_crop, descr="Crop the image from the drawn rectangle and selected parameter", color=ut.get_color("go") )
        layout.addWidget( crop_btn )

        self.setLayout( layout )


    def go_crop( self ):
        """ Performs the crop """
        if self.crop_layer is None:
            print( "No crop layer" )
            return
        ## Get the rectangle to crop
        if len(self.crop_layer.selected_data) > 0:
            crop_rect = self.crop_layer.data[list(self.crop_layer.selected_data)[0]]
        elif len(self.crop_layer.data) > 0:
            crop_rect = self.crop_layer.data[0]
        else:
            ut.show_warning("No drawn rectangle, cannot crop")
            return

        ## Crop and save the main image 
        crop_rect = crop_rect / self.mig.scaleXY ## adjust to coordinates
        crop_img = self.crop_rectangle( self.mig.image, crop_rect ) 
        crop_name = self.crop_name.text()
        self.mig.save_image( crop_img, imagename=crop_name, hasZ=True, imtype="uint16" )

        ## Crop and save the cell segmentation if any
        crop_junc = None
        if (self.mig.pop is not None) and (self.mig.pop.imgcell is not None):
            crop_junc = self.crop_rectangle( self.mig.pop.imgcell, crop_rect )
        else:
            juncfile = self.mig.junction_filename(dim=2, ifexist=True)
            if os.path.exists( juncfile ):
                crop_junc, scaleX, scaleZ, names = ut.open_image( juncfile, verbose=True )

        if crop_junc is not None:
            crop_junc_name = self.get_name( "_cells2D.tif" )
            self.mig.save_image( crop_junc, imagename=crop_junc_name, hasZ=False, imtype="uint16" )

        ## Crop and save the nuclei segmentation if any
        crop_nuc = None
        if (self.mig.pop is not None) and (self.mig.pop.imgnuc is not None):
            crop_nuc = self.crop_rectangle( self.mig.pop.imgnuc, crop_rect )
        else:
            nucfile = self.mig.nuclei_filename(ifexist=True)
            if os.path.exists( nucfile ):
                crop_nuc, scaleX, scaleZ, names = ut.open_image( nucfile, verbose=True )

        if crop_nuc is not None:
            crop_nuc_name = self.get_name( "_nuclei.tif" )
            self.mig.save_image( crop_nuc, imagename=crop_nuc_name, hasZ=True, imtype="uint16" )

        ## crop other image files if they exist
        files = ["_junction_projection.tif", "_junctionsStaining.tif", "_nucleiStaining.tif" ]
        for i in range(self.mig.nbchannels):
            files = files + ["_RNA"+str(i)+".tif"]
        for cfile in files:
            filename = self.mig.build_filename( cfile )
            if os.path.exists( filename ):
                tocrop, scaleX, scaleZ, names = ut.open_image( filename, verbose=True )
                crop = self.crop_rectangle( tocrop, crop_rect )
                cropfile_name = self.get_name( cfile )
                z = len(crop.shape) > 2
                self.mig.save_image( crop, imagename=cropfile_name, hasZ=z )
                

        print("Crop RNA segmentation from csv ")
        ## Crop RNA segmentation if it exists

        for chan in range(self.mig.nbchannels):
            rnafilename = self.mig.rna_filename( chan=chan, how=".csv", ifexist=True )
            crop_spots = []
            if os.path.exists( rnafilename ):
                ## Load the RNA spots
                rnaspotDict = ut.load_dictlist(rnafilename, verbose=True)
                for rnaspot in rnaspotDict:
                    if rnaspot.get("X") is not None:
                        if int(rnaspot["X"]) >= crop_rect[0][0] and int(rnaspot["X"]) <= crop_rect[2][0] and \
                           int(rnaspot["Y"]) >= crop_rect[0][1] and int(rnaspot["Y"]) <= crop_rect[2][1]:
                            ## RNA spot in the crop rectangle, keep it and adjust coordinates
                            rnaspot["X"] = int(rnaspot["X"]) - crop_rect[0][0]
                            rnaspot["Y"] = int(rnaspot["Y"]) - crop_rect[0][1]
                            crop_spots.append( rnaspot )
                ## Save the cropped RNA spots
                if len(crop_spots) > 0:
                    crop_rna_name = self.get_name( "_RNA"+str(chan)+".csv" )
                    ut.write_dict( crop_rna_name, crop_spots ) 
                    ut.show_info( "Cropped RNA spots saved in: "+crop_rna_name )


    def get_name( self, endname ):
        """ Build the name of the output file """
        imgname, imgdir, resdir = ut.extract_names( self.crop_name.text() )
        return os.path.join( resdir, imgname+endname )

    def crop_rectangle( self, img, crop_rect ):
        """ Apply the rectangle to crop img """
        ## 4d image: channel, z, y, x
        if len(img.shape) > 3:
            return img[ :,:,int(crop_rect[0][0]):int(crop_rect[2][0]), int(crop_rect[0][1]):int(crop_rect[2][1]) ]
        ## 3d image
        if len(img.shape) > 2:
            return img[ :,int(crop_rect[0][0]):int(crop_rect[2][0]), int(crop_rect[0][1]):int(crop_rect[2][1]) ]
        ## 2d image
        return img[ int(crop_rect[0][0]):int(crop_rect[2][0]), int(crop_rect[0][1]):int(crop_rect[2][1]) ]



    def finish( self ):
        """ Finish this option, close everything """
        ut.removeOverlayText( self.viewer )
        ut.remove_widget( self.viewer, "CropImage" )
        ut.remove_layer( self.viewer, "Crop" )

    def add_shape_layer( self ):
        """ Add the layer to draw the rectangle for the crop """
        self.viewer.dims.ndisplay = 2 ## force 2D view for shape drawing
        self.crop_layer = self.viewer.add_shapes( [], name="Crop" )
        text = "Draw rectangle to crop"
        self.crop_layer.mode = "add_rectangle"
        ut.showOverlayText( self.viewer, text )
