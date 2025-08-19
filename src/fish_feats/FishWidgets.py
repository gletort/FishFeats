import fish_feats.Utils as ut
from qtpy.QtWidgets import QPushButton, QCheckBox, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QComboBox, QSpinBox, QSlider, QGroupBox, QFileDialog # type: ignore from qtpy.QtCore import Qt # type: ignore
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

def add_check( check, checked, check_func=None, descr="" ):
    """ Add a checkbox with set parameters """
    cbox = QCheckBox( text=check )
    cbox.setToolTip( descr )
    if check_func is not None:
        cbox.stateChanged.connect( check_func )
    cbox.setChecked( checked )
    return cbox

def file_dialog( title, filetypes, directory=None ):
    """ Open a file dialog to select a file """
    if directory is None:
        directory = ''
    else:
        directory = str(directory)
    file_dialog = QFileDialog()
    file_dialog.setFileMode(QFileDialog.ExistingFile)
    file_dialog.setNameFilter(filetypes)
    file_dialog.setWindowTitle(title)
    file_dialog.setDirectory(directory)
    if file_dialog.exec_():
        filepath = file_dialog.selectedFiles()[0]
        if not filepath.endswith('.tif'):
            raise ValueError("Selected file is not a .tif file")
    else:
        filepath = None
    return filepath 
