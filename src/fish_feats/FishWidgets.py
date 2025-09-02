import fish_feats.Utils as ut
import os
from qtpy.QtWidgets import QPushButton, QCheckBox, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QComboBox, QSpinBox, QSlider, QGroupBox, QFileDialog, QListWidget, QAbstractItemView # type: ignore from qtpy.QtCore import Qt # type: ignore
from qtpy.QtCore import Qt # type: ignore

def help_button( link, description="", display_settings=None ):
    """ Create a new Help button with given parameter """
    def show_doc():
        """ Open documentation page """
        ut.show_documentation_page( link )

    help_btn = QPushButton( "help" )
    if description == "":
        help_btn.setToolTip( "Open Fish&Feats documentation" )
        help_btn.setStatusTip( "Open Fish&Feats documentation" )
    else:
        help_btn.setToolTip( description )
        help_btn.setStatusTip( description )
    help_btn.clicked.connect( show_doc )
    if display_settings is not None:
        color = display_settings["Help button"]
        help_btn.setStyleSheet( 'QPushButton {background-color: '+color+'}' )
    else:
        color = ut.get_color( "help" )
        help_btn.setStyleSheet( 'QPushButton {background-color: '+color+'}' )
    return help_btn


def checkgroup_help( name, checked, descr, help_link, display_settings=None, groupnb=None ):
    """ Create a group that can be show/hide with checkbox and an help button """
    group = QGroupBox()
    chbox = QCheckBox( text=name )

    ## set group and checkbox to the same specific color
    if (groupnb is not None) and (display_settings is not None):
        if groupnb in display_settings:
            color = display_settings[groupnb]
            group.setStyleSheet( 'QGroupBox {background-color: '+color+'}' )
            chbox.setStyleSheet( 'QCheckBox::indicator {background-color: '+color+'}' )
    
    def show_hide():
        group.setVisible( chbox.isChecked() )

    line = QHBoxLayout()
    ## create checkbox
    chbox.setToolTip( descr )
    line.addWidget( chbox )
    chbox.stateChanged.connect( show_hide )
    chbox.setChecked( checked )
    ## create button
    if help_link is not None:
        help_btn = help_button( help_link, "", display_settings )
        line.addWidget( help_btn )
    return line, chbox, group

def group_layout( name, descr="", color=None ):
    """ Create a group layout with a name and a description """
    group = QGroupBox( name )
    if descr != "":
        group.setToolTip( descr )
        group.setStatusTip( descr )
    if color is not None:
        group.setStyleSheet( 'QGroupBox {background-color: '+color+'}' )
    layout = QVBoxLayout()
    return group, layout

def add_multiple_list( label, descr="" ):
    """ List interface, with possibility of multiple selection """
    list_widget = QListWidget()
    list_widget.setSelectionMode(QAbstractItemView.MultiSelection)
    layout = QVBoxLayout()
    layout.addWidget(QLabel(label))
    layout.addWidget(list_widget)
    if descr != "":
        list_widget.setToolTip( descr )
    return layout, list_widget

def add_button( btn, btn_func, descr="", color=None ):
    """ Add a button connected to an action when pushed """
    cbtn = QPushButton( btn )
    if btn_func is not None:
        cbtn.clicked.connect( btn_func )
    if descr != "":
        cbtn.setToolTip( descr )
    else:
        cbtn.setToolTip( "Click to perform action" )
    if color is not None:
        cbtn.setStyleSheet( 'QPushButton {background-color: '+color+'}' )
    return cbtn

def double_button( btna, btnb ):
    """ Create a line with two buttons """
    line = QHBoxLayout()
    line.addWidget( btna )
    line.addWidget( btnb )
    return line

def add_label( lab, descr="" ):
    """ Create a label object """
    label = QLabel( lab )
    if descr != "":
        label.setToolTip( descr )
        label.setStatusTip( descr )
    return label


def label_button( btn, btn_func, label="", descr="", color=None ):
    """ Create a line with a label and a button """
    line = QHBoxLayout()
    lab = QLabel()
    lab.setText( label )
    if descr != "":
        lab.setToolTip( descr )
        lab.setStatusTip( descr )
    btn = add_button( btn, btn_func, descr, color )
    line.addWidget( btn )
    line.addWidget( lab )
    return line, btn, lab


def line_button_help( btn, btn_func, descr="", help_link=None, color=None ):
    """ Create a line with a button and an help button """
    line = QHBoxLayout()
    btn = add_button( btn, btn_func, descr, color )
    line.addWidget( btn )
    if help_link is not None:
        help_btn = help_button( help_link, "Open online documentation", None )
        line.addWidget( help_btn )
    return line, btn

def list_line( label, descr="", func=None ):
    """ Create a layout line with a choice list to edit (non editable name + list part ) """
    line = QHBoxLayout()
    ## Value name
    lab = QLabel()
    lab.setText( label )
    line.addWidget( lab )
    if descr != "":
        lab.setToolTip( descr )
        lab.setStatusTip( descr )
    ## Value editable part
    value = QComboBox()
    line.addWidget( value )
    if func is not None:
        value.currentIndexChanged.connect( func )
    return line, value

def add_value( default_value, descr="" ):
    """ Editable value """
    value = QLineEdit()
    value.setText( str(default_value) )
    if descr != "":
        value.setToolTip( descr )
    return value

def double_value_line( labela, default_valuea, labelb, default_valueb, descr="" ):
    """ Layout with two values to edit """
    line = QHBoxLayout()
    ## first
    laba = QLabel()
    laba.setText( labela )
    line.addWidget( laba )
    valuea = QLineEdit()
    valuea.setText( str(default_valuea) )
    line.addWidget( valuea )
    ## second
    labb = QLabel()
    labb.setText( labelb )
    line.addWidget( labb )
    valueb = QLineEdit()
    valueb.setText( str(default_valueb) )
    line.addWidget( valueb )
    if descr != "":
        laba.setToolTip( descr )
        labb.setToolTip( descr )
    return line, valuea, valueb

def value_line( label, default_value, descr="" ):
    """ Create a layout line with a value to edit (non editable name + value part ) """
    line = QHBoxLayout()
    ## Value name
    lab = QLabel()
    lab.setText( label )
    line.addWidget( lab )
    if descr != "":
        lab.setToolTip( descr )
    ## Value editable part
    value = QLineEdit()
    value.setText( str(default_value) )
    line.addWidget( value )
    return line, value

def spinner_line( name, minval, maxval, step, value, changefunc=None, descr="" ):
    """ Line with a spinbox """
    line = QHBoxLayout()
    ## add name if any
    if name is not None:
        lab = QLabel()
        lab.setText( name )
        line.addWidget( lab )
    ## add spinbox
    spinner = QSpinBox()
    spinner.setRange( minval, maxval )
    spinner.setSingleStep(1)
    spinner.setValue( int(value) )
    if changefunc is not None:
        spinner.valueChanged.connect( changefunc )
    if descr != "":
        spinner.setToolTip( descr )
    line.addWidget( spinner )
    return line, spinner

def slider_line( name, minval, maxval, step, value, show_value=False, slidefunc=None, descr="", div=1 ):
    """ Line with a text and a slider """
    line = QHBoxLayout()
    ## add name if any
    if name is not None:
        lab = QLabel()
        lab.setText( name )
        line.addWidget( lab )
    ## add slider
    slider =  QSlider( Qt.Horizontal )
    slider.setMinimum( int(minval*div) )
    slider.setMaximum( int(maxval*div) )
    slider.setSingleStep( int(step*div) )
    slider.setValue( int(value*div) )
    if slidefunc is not None:
        slider.valueChanged.connect( slidefunc )
    if descr != "":
        slider.setToolTip( descr )
        lab.setToolTip( descr )
    if show_value:
        lab = QLabel(""+str(value*1.0))
        line.addWidget( lab )
        slider.valueChanged.connect( lambda: lab.setText( ""+str(slider.value()*1.0/div) ) )
    line.addWidget( slider )
    return line, slider

def double_widget( wida, widb ):
    """ Create a line layout with the two widgets """
    line = QHBoxLayout()
    line.addWidget( wida )
    line.addWidget( widb )
    return line

def check_value_line( name, checked,  value_name, value_default, descr="" ):
    """ Line with value visible only if checked """
    line = QHBoxLayout()
    cbox = QCheckBox( text=name )
    cbox.setChecked( checked )
    line.addWidget( cbox )
    lab = QLabel()
    lab.setText( value_name )
    line.addWidget( lab )
    value = QLineEdit()
    value.setText( str(value_default) )
    line.addWidget( value )
    if descr != "":
        lab.setToolTip( descr )
    cbox.stateChanged.connect( lambda state: value.setVisible( state == Qt.Checked ) )
    cbox.stateChanged.connect( lambda state: lab.setVisible( state == Qt.Checked ) )
    value.setVisible( checked )
    lab.setVisible( checked )
    return line, cbox, value

def add_check( check, checked, check_func=None, descr="" ):
    """ Add a checkbox with set parameters """
    cbox = QCheckBox( text=check )
    cbox.setToolTip( descr )
    if check_func is not None:
        cbox.stateChanged.connect( check_func )
    cbox.setChecked( checked )
    return cbox

def file_line( title, default_path="", dial_msg="Choose file", filetype="All (*)", descr="" ):
    """ interface line with browse btn and current path """
    line = QHBoxLayout()
    lab = add_label( title, descr )
    line.addWidget( lab )
    value = QLineEdit()
    value.setText( default_path )
    #value.setMaximumWidth(20)
    line.addWidget( value )
    btn = QPushButton( "Browse" )
    btn.clicked.connect( lambda: browse_file( value, dial_msg, filetype, default_path ) )
    line.addWidget( btn )
    return line, value

def dir_line( title, default_path="", dial_msg="Choose directory", descr="" ):
    """ interface line with browse btn and current path """
    line = QHBoxLayout()
    lab = add_label( title, descr )
    line.addWidget( lab )
    value = QLineEdit()
    value.setText( default_path )
    line.addWidget( value )
    btn = QPushButton( "Browse" )
    btn.clicked.connect( lambda: browse_dir( value, dial_msg, default_path ) )
    line.addWidget( btn )
    return line, value

def browse_file( value, dial_msg, filetype, default_path ):
    """ Open a file dialog to select a file """
    filepath = file_dialog( dial_msg, filetype, directory=default_path )
    if filepath is not None:
        value.setText( filepath )   

def browse_dir( value, dial_msg, default_path ):
    """ Open a file dialog to select a directory """
    dirpath = dir_dialog( dial_msg, directory=default_path )
    if dirpath is not None:
        value.setText( dirpath )

def dir_dialog( title, directory=None ):
    """ Opens a dialog to select a folder """
    if directory is None:
        directory = ''
    else:
        directory = str( os.path.dirname(directory) )
    file_dialog = QFileDialog()
    file_dialog.setFileMode(QFileDialog.Directory)
    #file_dialog.setOption(QFileDialog.ShowDirsOnly, True)
    file_dialog.setWindowTitle(title)
    file_dialog.setDirectory(directory)
    if file_dialog.exec_():
        filepath = file_dialog.selectedFiles()[0]
    else:
        filepath = None
    return filepath 

def file_dialog( title, filetypes, directory=None ):
    """ Open a file dialog to select a file """
    if directory is None:
        directory = ''
    else:
        directory = str( os.path.dirname(directory) )
    file_dialog = QFileDialog()
    file_dialog.setFileMode(QFileDialog.ExistingFile)
    file_dialog.setNameFilter(filetypes)
    file_dialog.setWindowTitle(title)
    file_dialog.setDirectory(directory)
    if file_dialog.exec_():
        filepath = file_dialog.selectedFiles()[0]
        #if not filepath.endswith('.tif'):
        #    raise ValueError("Selected file is not a .tif file")
    else:
        filepath = None
    return filepath 
