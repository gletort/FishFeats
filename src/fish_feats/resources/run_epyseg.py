import logging
import os
appose_mode = 'task' in globals()

if not appose_mode:
    from appose.python_worker import Task
    task = Task()
    input_folder = "./"

class ApposeLogHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        task.update( message=msg )

def setup_logger( name="" ):
    logger = logging.getLogger(name)
    handler = ApposeLogHandler()
    formatter = logging.Formatter('[FishFeats-Epyseg]-%(message)s')
    handler.setFormatter( formatter )
    logger.addHandler(handler)
    logger.setLevel( 20 )
    return logger


logger = setup_logger()    
logger.info("Starting segmentation")

# libraries loaded checking epyseg to see if everything is functional
try:
    logger.info("Initializing deepl")
    import epyseg.deeplearning.deepl as deepl
    deepl.logger = logger 
    logger.info("Initializing EZ")
    from epyseg.deeplearning.deepl import EZDeepLearning
    logger.info("Initialized")
    deepTA = EZDeepLearning()
    logger.info("Initialized all")
except Exception as e:
    logger.info( 'EPySeg failed to load. '+e )
    
# Load a pre-trained model
pretrained_model_name = 'Linknet-vgg16-sigmoid-v2'
pretrained_model_parameters = deepTA.pretrained_models[pretrained_model_name]

logger.info("Preparing epyseg model")

deepTA.load_or_build(model=None, model_weights=None,
                             architecture=pretrained_model_parameters['architecture'], backbone=pretrained_model_parameters['backbone'],
                             activation=pretrained_model_parameters['activation'], classes=pretrained_model_parameters['classes'],
                             input_width=pretrained_model_parameters['input_width'], input_height=pretrained_model_parameters['input_height'],
                             input_channels=pretrained_model_parameters['input_channels'],pretraining=pretrained_model_name)

input_val_width = 256
input_val_height = 256
    
input_shape = deepTA.get_inputs_shape()
output_shape = deepTA.get_outputs_shape()
if input_shape[0][-2] is not None:
    input_val_width=input_shape[0][-2]
if input_shape[0][-3] is not None:
    input_val_height=input_shape[0][-3]
#print(input_shape)
deepTA.compile(optimizer='adam', loss='bce_jaccard_loss', metrics=['iou_score'])
      
range_input = [0,1]
input_normalization = {'method': 'Rescaling (min-max normalization)',
                        'individual_channels': True, 'range': range_input, 'clip': True} 

predict_generator = deepTA.get_predict_generator(
            inputs=[input_folder], input_shape=input_shape,
            output_shape=output_shape, 
            default_input_tile_width=input_val_width, 
            default_input_tile_height=input_val_height,
            tile_width_overlap=32,
            tile_height_overlap=32, 
            input_normalization=input_normalization, 
            clip_by_frequency={'lower_cutoff': None, 'upper_cutoff': None, 'channel_mode': True} )

post_process_parameters={}
post_process_parameters['filter'] = None
post_process_parameters['correction_factor'] = 1
post_process_parameters['restore_safe_cells'] = False ## no eff
post_process_parameters['cutoff_cell_fusion'] = None
post_proc_method = 'Rescaling (min-max normalization)'
post_process_parameters['post_process_algorithm'] = post_proc_method
post_process_parameters['threshold'] = None  # None means autothrehsold # maybe add more options some day

predict_output_folder = os.path.join(input_folder, 'predict')

logger.info("Running epyseg prediction")
deepTA.predict(predict_generator, 
                output_shape, 
                predict_output_folder=predict_output_folder,
                batch_size=1, **post_process_parameters)
    
deepTA.clear_mem()
if not os.access(predict_output_folder, os.W_OK):
    os.chmod(predict_output_folder, stat.S_IWUSR)
#deepTA = None
del deepTA