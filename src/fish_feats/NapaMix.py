import fish_feats.Utils as ut
import fish_feats.FishWidgets as fwid
import fish_feats.Configuration as cf
import numpy as np
import os
from qtpy.QtWidgets import QVBoxLayout, QWidget 

class CheckScale( QWidget):
    """
        Handle the update of metadata parameters, choice of channel
    """

    def __init__( self, viewer, mig, cfg, load_all_previous, separation, next_step ):
        """
            Initialize the interface to set metadata
        """
        self.viewer = viewer
        self.mig = mig
        self.cfg = cfg
        self.load_all_previous_files = load_all_previous
        self.divorceJunctionsNuclei = separation
        self.getChoices = next_step

        super().__init__()
        layout = QVBoxLayout()

        if self.cfg is None:
            self.cfg = cf.Configuration(mig.save_filename(), show=False)

        ## load saved parameters
        if self.cfg.has_config():
            self.cfg.read_scale(mig)
        zdir = "top high z"
        if self.mig.zdirection == 1:
            zdir = "top low z"
        
        ## get the scaling in XY
        line_scalexy, self.scaleXY = fwid.value_line( "XY scale (um/pixel):", self.mig.scaleXY, descr="Set the scale in XY (um/pixel)" )
        layout.addLayout( line_scalexy )
        
        ## get the scaling in Z
        line_scalez, self.scaleZ = fwid.value_line( "Z scale (um/pixel):", self.mig.scaleZ, descr="Set the scale in Z (um/pixel)" )
        layout.addLayout( line_scalez )

        ## get the direction of Z
        line_zdir, self.zdirection = fwid.list_line( "Z direction:", descr="Choose the direction of Z" )
        layout.addLayout( line_zdir )
        self.zdirection.addItems( ["top high z", "top low z"] )
        self.zdirection.setCurrentText( zdir )

        ## get the channel number of junction if any
        line_junchan, self.junchan = fwid.list_line( "Junction channel:", descr="Choose the channel number of the junction staining, or None if no junction staining" )
        layout.addLayout( line_junchan )
        self.junchan.addItem( "None" )
        for chan in range(self.mig.nbchannels):
            self.junchan.addItem( str(chan) )
        self.junchan.setCurrentText( str(self.mig.junchan) )

        ## get the channel number of nuclei if any
        line_nucchan, self.nucchan = fwid.list_line( "Nuclei channel:", descr="Choose the channel number of the nuclei staining, or None if no nuclei staining" )
        layout.addLayout( line_nucchan )
        self.nucchan.addItem( "None" )
        for chan in range(self.mig.nbchannels):
            self.nucchan.addItem( str(chan) )
        self.nucchan.setCurrentText( str(self.mig.nucchan) )

        ## load previous results
        self.load_previous = fwid.add_check( "Load previous", True, None, descr="Load previously saved files (in results folder) for the current image" )
        layout.addWidget( self.load_previous )

        ## button to open help
        help_btn = fwid.add_button( "Help", self.open_help, descr="Open the help documentation", color=ut.get_color("help") )
        ## button to update the metadata and channel and go to next step
        update_btn = fwid.add_button( "Update", self.update_metadata, descr="Update the metadata and channel choice", color=ut.get_color("go") )
        btn_line = fwid.double_button( update_btn, help_btn )

        layout.addLayout( btn_line )
        self.setLayout( layout )
        self.show_helptext()

    def update_metadata( self ):
        """ Update the metadata based on selected parameters """

        ## read the parameters
        self.mig.scaleXY = float( self.scaleXY.text() )
        self.mig.scaleZ = float( self.scaleZ.text() )
        if self.zdirection.currentText() == "top high z":
            self.mig.zdirection = 1
        else:
            self.mig.zdirection = 1
        self.mig.junchan = self.junchan.currentText()
        if self.mig.junchan == "None":
            self.mig.junchan = None
        else:
            self.mig.junchan = int(self.mig.junchan)
        self.mig.nucchan = self.nucchan.currentText()
        if self.mig.nucchan == "None":
            self.mig.nucchan = None
        else:
            self.mig.nucchan = int(self.mig.nucchan)

        ## udpate the view scale        
        for chan in range( self.mig.nbchannels ):
            self.viewer.layers['originalChannel'+str(chan)].scale = [self.mig.scaleZ, self.mig.scaleXY, self.mig.scaleXY]

        ## clean the view
        ut.remove_all_widget( self.viewer )
        ut.removeOverlayText( self.viewer )

        ## update the config
        self.cfg.addGroupParameter("ImageScalings")
        self.cfg.addParameter("ImageScalings", "scalexy", self.mig.scaleXY)
        self.cfg.addParameter("ImageScalings", "scalez", self.mig.scaleZ)
        self.cfg.addParameter("ImageScalings", "direction", self.mig.zdirection)
        self.cfg.addParameter("ImageScalings", "junction_channel", self.mig.junchan)
        self.cfg.addParameter("ImageScalings", "nuclei_channel", self.mig.nucchan)
        self.viewer.grid.enabled = False
        self.cfg.write_parameterfile()

        if self.load_previous.isChecked():
            self.load_all_previous_files()
            return None
        
        if self.mig.should_separate():
            ut.show_info("Junctions and nuclei staining in the same color channel, need to separate them")
            self.divorceJunctionsNuclei()

        if not ut.has_widget( self.viewer, "Main" ):
            self.getChoices()

    def show_helptext( self ):
        """ Show scalings choice help text """
        help_text = ut.help_shortcut( "view" )
        help_text += ut.scale_shortcuts()
        ut.showOverlayText( self.viewer, help_text )

    def open_help( self ):
        """ Open doc webpage for Image scalings """
        ut.show_documentation_page( "Image-scalings" )

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
