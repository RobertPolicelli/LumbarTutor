import os, sys, glob
from __main__ import vtk, qt, ctk, slicer
from functools import partial

from Guidelet import GuideletLoadable, GuideletLogic, GuideletTest, GuideletWidget
from Guidelet import Guidelet
import logging
import time

class LumbarTutor(GuideletLoadable):
  """Uses GuideletLoadable class, available at:
  """

  def __init__(self, parent):
    GuideletLoadable.__init__(self, parent)
    self.parent.title = "Lumbar Tutor"
    self.parent.categories = [ "Training" ]
    self.parent.dependencies = []
    self.parent.contributors = ["Matthew S. Holden (Perk Lab, Queen's University)"]
    self.parent.helpText = """  """
    self.parent.acknowledgementText = """  """


class LumbarTutorWidget(GuideletWidget):
  """Uses GuideletWidget base class, available at:
  """

  def __init__(self, parent = None):
    GuideletWidget.__init__(self, parent)

  def setup(self):
    GuideletWidget.setup(self)

  def addLauncherWidgets(self):
    GuideletWidget.addLauncherWidgets(self)


  def onConfigurationChanged(self, selectedConfigurationName):
    GuideletWidget.onConfigurationChanged(self, selectedConfigurationName)
    #settings = slicer.app.userSettings()


  def createGuideletInstance(self):
    return LumbarTutorGuidelet(None, self.guideletLogic, self.selectedConfigurationName)


  def createGuideletLogic(self):
    return LumbarTutorLogic()


class LumbarTutorLogic(GuideletLogic):
  """Uses GuideletLogic base class, available at:
  """ #TODO add path

  def __init__(self, parent = None):
    GuideletLogic.__init__(self, parent)
    
    self.addValuesToDefaultConfiguration()
    self.addValuesToNo3DGuidanceConfiguration()

    
  def addValuesToDefaultConfiguration(self):
    GuideletLogic.addValuesToDefaultConfiguration(self)
    moduleDir = os.path.dirname(slicer.modules.lumbartutor.path)

    settingsList = {
                   'StyleSheet' : os.path.join( moduleDir, 'Resources/StyleSheets/LumbarTutorStyle.qss' ), #overwrites the default setting param of base
                   'TestMode' : 'False',
                   'RecordingFilenamePrefix' : 'LumbarTutorRec-',
                   'SavedScenesDirectory': os.path.join( moduleDir, 'SavedScenes' ), #overwrites the default setting param of base
                   'PlusWebcamServerHostNamePort': 'localhost:18945',
                   }
                   
    self.updateSettings(settingsList, 'Default')
    
  ## Set up a custom configuration   
  def addValuesToNo3DGuidanceConfiguration(self):
    settingsList = {}
    self.updateUserPreferencesFromSettings( settingsList, 'Default' ) # Copy values from the default configuration

    settingsList[ 'CalibrationLayout' ] = Guidelet.VIEW_ULTRASOUND_CAM_3D
    settingsList[ 'ProcedureLayout' ] = Guidelet.VIEW_ULTRASOUND
    settingsList[ 'ResultsLayout' ] = Guidelet.VIEW_ULTRASOUND_CAM_3D

    self.updateSettings( settingsList, 'No 3D Guidance' )
  

  # This function allows us to conveniently copy settings from another configuration (e.g. Default)
  # TODO: Is there something like this already in the GuideletLogic class?
  def updateUserPreferencesFromSettings( self, settingsNameValueMap, configurationName = None ):
    settings = slicer.app.userSettings()
    
    if not configurationName:
      groupString = self.moduleName
    else:
      groupString = self.moduleName + '/Configurations/' + configurationName
      
    settings.beginGroup( groupString )
    for name in settings.allKeys():
      settingsNameValueMap[ name ] = settings.value( name )
    settings.endGroup()



class LumbarTutorTest(GuideletTest):
  """This is the test case for your scripted module.
  """

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    GuideletTest.runTest(self)
    #self.test_LumbarTutor1() #add applet specific tests here


class LumbarTutorGuidelet(Guidelet):

  def __init__(self, parent, logic, configurationName='Default'):
    self.calibrationCollapsibleButton = None
    self.resultsCollapsibleButton = None

    Guidelet.__init__(self, parent, logic, configurationName)
    logging.debug('LumbarTutorGuidelet.__init__')
    
    # Set up the webcam connection
    # TODO: Guidelet is not really designed to handle multiple connector nodes, but we need one for the ultrasound and one for the webcam
    # Let us create another one here for the webcam
    # Probably the Guidelet should eventually be updated to handle these cases, as we often have tracked ultrasound and webcam anymore
    try:
      self.webcamConnectorNode = slicer.util.getNode('PlusWebcamConnector')
    except slicer.util.MRMLNodeNotFoundException:
      self.webcamConnectorNode = self.createPlusConnector( self.parameterNode.GetParameter('PlusWebcamServerHostNamePort') )
      self.webcamConnectorNode.SetName( "PlusWebcamConnector" )
    self.webcamConnectorNode.Start()
    
    moduleDirectoryPath = slicer.modules.lumbartutor.path.replace('LumbarTutor.py', '')

    # Set up main frame
    self.sliceletDockWidget.setObjectName('LumbarTutorPanel')
    self.sliceletDockWidget.setWindowTitle('Lumbar Tutor')
    self.mainWindow.setWindowTitle('Lumbar Tutor')
    self.mainWindow.windowIcon = qt.QIcon(moduleDirectoryPath + '/Resources/Icons/LumbarTutor.png')

    self.pivotCalibrationLogic = slicer.modules.pivotcalibration.logic()

    self.navigationView = self.VIEW_ULTRASOUND_CAM_3D
    self.updateNavigationView()

    self.usMarkersPropertiesDict = {}
    self.setupSliceUSMarkers("Red")

    # Setting button open on startup.
    self.calibrationCollapsibleButton.setProperty('collapsed', True)


  def createFeaturePanels(self):
    # 1. Initialize the base Guidelet panels (this safely boots up core logic)
    featurePanelList = Guidelet.createFeaturePanels(self)
    
    # 2. Hide the default Ultrasound tab so it doesn't show up on screen
    self.ultrasoundCollapsibleButton.setVisible(False)

    # 3. Setup Anatomy Tab (Top)
    self.anatomyCollapsibleButton = ctk.ctkCollapsibleButton()
    self.setupAnatomyPanel()

    # 4. Setup Calibration Tab (Middle)
    self.calibrationCollapsibleButton = ctk.ctkCollapsibleButton()
    self.calibrationSetupPanel()

    # 5. Setup Procedure Tab (Bottom)
    self.procedureCollapsibleButton = ctk.ctkCollapsibleButton()
    self.setupProcedurePanel()

    # Tell Slicer to exclusively use our three custom panels
    featurePanelList = [self.anatomyCollapsibleButton, self.calibrationCollapsibleButton, self.procedureCollapsibleButton]

    self.anatomyCollapsibleButton.setProperty('collapsed', False)
    self.calibrationCollapsibleButton.setProperty('collapsed', True) 
    self.procedureCollapsibleButton.setProperty('collapsed', True)   
    self.advancedCollapsibleButton.setProperty('collapsed', True)    # Starts CLOSED
    return featurePanelList


  def __del__(self):#common
    self.cleanup()


  # Clean up when guidelet is closed
  def cleanup(self):#common
    Guidelet.cleanup(self)
    logging.debug('cleanup')


  def setupConnections(self):
    logging.debug('LumbarTutorGuidelet.setupConnections()')
    Guidelet.setupConnections(self)
    
    # Inside setupConnections(self):

    self.calibrationCollapsibleButton.connect('toggled(bool)', self.onCalibrationSetupPanelToggled)
    self.procedureCollapsibleButton.connect('toggled(bool)', self.onProcedureTabToggled)
    self.anatomyCollapsibleButton.connect('toggled(bool)', self.onAnatomyTabToggled)
    
    self.l3Button.connect('clicked(bool)', self.onL3Clicked)
    self.l4Button.connect('clicked(bool)', self.onL4Clicked)
    self.l5Button.connect('clicked(bool)', self.onL5Clicked)
    self.ligamentumButton.connect('clicked(bool)', self.onLigamentumClicked)
    self.spinalCordButton.connect('clicked(bool)', self.onSpinalCordClicked)
    
    self.insStep1Button.connect('clicked(bool)', self.onInsStep1Clicked)
    self.insStep2Button.connect('clicked(bool)', self.onInsStep2Clicked)
    self.insStep3Button.connect('clicked(bool)', self.onInsStep3Clicked)
    self.insStep4Button.connect('clicked(bool)', self.onInsStep4Clicked)
    
    self.fluidStep1Button.connect('clicked(bool)', self.onFluidStep1Clicked)
    self.fluidStep2Button.connect('clicked(bool)', self.onFluidStep2Clicked)
    self.fluidStep3Button.connect('clicked(bool)', self.onFluidStep3Clicked)
    self.fluidStep4Button.connect('clicked(bool)', self.onFluidStep4Clicked)

    self.compStep1Button.connect('clicked(bool)', self.onCompStep1Clicked)
    self.compStep2Button.connect('clicked(bool)', self.onCompStep2Clicked)
    self.compStep3Button.connect('clicked(bool)', self.onCompStep3Clicked)

    
    self.pivotCalibrationButton.connect('clicked(bool)', self.onNeedleCalibrationClicked)
    self.spinCalibrationButton.connect('clicked(bool)', self.onSpinCalibrationClicked)    
    self.pivotSamplingTimer.connect('timeout()', self.onPivotSamplingTimeout)
    
    self.viewAlignmentButton.connect('clicked()', self.align3DView)
    
    self.step1Button.connect('clicked(bool)', self.onStep1Clicked)
    self.step2Button.connect('clicked(bool)', self.onStep2Clicked)
    self.step3Button.connect('clicked(bool)', self.onStep3Clicked)
    self.step4Button.connect('clicked(bool)', self.onStep4Clicked)
    self.step5Button.connect('clicked(bool)', self.onStep5Clicked)
    
    # Keyboard shortcuts
    if ( not hasattr( self, 'startStopShortcutPlus' ) or self.startStopShortcutPlus is None ):
      self.startStopShortcutPlus = qt.QShortcut( qt.QKeySequence( "+" ), self.sliceletDockWidget )
    self.startStopShortcutPlus.connect('activated()', self.ultrasound.startStopRecordingButton.click )
    # --- Advance Step Keyboard Shortcut ---
    if not hasattr(self, 'advanceStepShortcut') or self.advanceStepShortcut is None:
      self.advanceStepShortcut = qt.QShortcut(qt.QKeySequence("p"), self.sliceletDockWidget)
    self.advanceStepShortcut.connect('activated()', self.onAdvanceStepShortcut)


  def setupScene(self): #applet specific
    logging.debug('setupScene')

    # This will automatically create the ReferenceToRas transform
    Guidelet.setupScene(self)
    self.referenceToRas = self.ultrasound.referenceToRas
    
    moduleDir = os.path.dirname(slicer.modules.lumbartutor.path)

    # Transforms
    logging.debug('Create transforms')    

    # The transforms to be received from PLUS
    try:
      self.probeToReference = slicer.util.getNode('ProbeToReference')
    except slicer.util.MRMLNodeNotFoundException:
      self.probeToReference = slicer.vtkMRMLLinearTransformNode()
      self.probeToReference.SetName("ProbeToReference")
      slicer.mrmlScene.AddNode(self.probeToReference)

    try:
      self.needleToReference = slicer.util.getNode('NeedleToReference')
    except slicer.util.MRMLNodeNotFoundException:
      self.needleToReference = slicer.vtkMRMLLinearTransformNode()
      self.needleToReference.SetName('NeedleToReference')
      slicer.mrmlScene.AddNode(self.needleToReference)

    try:
      self.imageToProbe = slicer.util.getNode('ImageToProbe')
    except slicer.util.MRMLNodeNotFoundException:
      imageToProbeFilePath = os.path.join(moduleDir, 'Resources', 'ImageToProbe.h5')

      try:
        self.imageToProbe = slicer.util.loadTransform(imageToProbeFilePath)
        self.imageToProbe.SetName("ImageToProbe")
      except:
        logging.error('Could not read ImageToProbe!')
      '''self.imageToProbe = slicer.vtkMRMLLinearTransformNode()
      self.imageToProbe.SetName('ImageToProbe')
      slicer.mrmlScene.AddNode(self.imageToProbe)'''

    # Transforms to be computed from calibration
    try:
      self.probeModelToProbe = slicer.util.getNode('ProbeModelToProbe')
    except slicer.util.MRMLNodeNotFoundException:
      probeToReferenceFilePath = os.path.join(moduleDir, 'Resources', 'ProbeModelToProbe_L12_1.h5')

      try:
        self.probeModelToProbe = slicer.util.loadTransform(probeToReferenceFilePath)
        self.probeModelToProbe.SetName("ProbeModelToProbe")
      except:
        logging.error('Could not read probe model to probe transform for Sonix L14-5!')

    try:
      self.ultrasound_flip = slicer.util.getNode('Flip2')
    except slicer.util.MRMLNodeNotFoundException:
      flip2FilePath = os.path.join(moduleDir, 'Resources', 'Flip2.h5')

      try:
        self.ultrasound_flip = slicer.util.loadTransform(flip2FilePath)
        self.ultrasound_flip.SetName("Flip2")
      except:
        logging.error('Could not read Flip2 transform for ultrasound probe')

    try:
      self.needleTipToNeedle = slicer.util.getNode('NeedleTipToNeedle')
    except slicer.util.MRMLNodeNotFoundException:
      self.needleTipToNeedle = slicer.vtkMRMLLinearTransformNode()
      self.needleTipToNeedle.SetName('NeedleTipToNeedle')
      m = self.logic.readTransformFromSettings('NeedleTipToNeedle', self.configurationName)
      if m:
        self.needleTipToNeedle.SetMatrixTransformToParent(m)
      slicer.mrmlScene.AddNode(self.needleTipToNeedle)

    # Models


    logging.debug('Create models')

    try:
      self.usProbeModel = slicer.util.getNode('UsProbe')
    except slicer.util.MRMLNodeNotFoundException:
      modelFilePath = os.path.join(moduleDir, 'Resources', 'Telemed_L12.stl')
      self.usProbeModel = slicer.util.loadModel(modelFilePath)
      self.usProbeModel.SetName('UsProbe')
      self.usProbeModel.GetDisplayNode().SetColor(0.9, 0.9, 0.9)

    try:
      self.needleModel = slicer.util.getNode('NeedleModel')
    except slicer.util.MRMLNodeNotFoundException:
      self.needleModel = slicer.modules.createmodels.logic().CreateNeedle(80, 1.0, 0, 0)
      self.needleModel.SetName('NeedleModel')

    try:
      self.spineModel = slicer.util.getNode('SpineModel')
    except slicer.util.MRMLNodeNotFoundException:
      self.spineModel = slicer.vtkMRMLModelNode()
      self.spineModel.SetName('SpineModel')
      self.spineModel.SetScene(slicer.mrmlScene)
      slicer.mrmlScene.AddNode(self.spineModel)
      self.spineModel.CreateDefaultDisplayNodes()
      self.spineModel.GetDisplayNode().SetColor(0.95, 0.85, 0.55) #bone
      self.spineModel.SetAndObservePolyData( vtk.vtkPolyData() )

    try:
      self.tissueModel = slicer.util.getNode('TissueModel')
    except slicer.util.MRMLNodeNotFoundException:
      self.tissueModel = slicer.vtkMRMLModelNode()
      self.tissueModel.SetName('TissueModel')
      self.tissueModel.SetScene(slicer.mrmlScene)
      slicer.mrmlScene.AddNode(self.tissueModel)
      self.tissueModel.CreateDefaultDisplayNodes()
      self.tissueModel.GetDisplayNode().SetColor(0.70, 0.50, 0.40) #skin
      self.tissueModel.GetDisplayNode().SetOpacity(0.4)
      self.tissueModel.SetAndObservePolyData( vtk.vtkPolyData() )
      
    # Images
    logging.debug('Create images')

    try:
      self.ultrasound_Ultrasound = slicer.util.getNode('Image_Image') # Max 20 character name due to OpenIGTLink standard
    except slicer.util.MRMLNodeNotFoundException:
      self.ultrasound_Ultrasound = slicer.vtkMRMLScalarVolumeNode()
      self.ultrasound_Ultrasound.SetName('Image_Image')
      slicer.mrmlScene.AddNode(self.ultrasound_Ultrasound)

    try:
      self.webcam_Webcam = slicer.util.getNode('Webcam_Reference')
    except slicer.util.MRMLNodeNotFoundException:
      self.webcam_Webcam = slicer.vtkMRMLStreamingVolumeNode()
      self.webcam_Webcam.SetName('Webcam_Reference')
      slicer.mrmlScene.AddNode(self.webcam_Webcam)

    self.displayImageInSliceViewer(self.ultrasound_Ultrasound.GetID(), "Red", False, 180)
    self.displayImageInSliceViewer(self.webcam_Webcam.GetID(), "Yellow", True, 0)
    
    # Load the spine "scenes"
    logging.debug('Create spine scenes')
    
    '''spineScenes = glob.glob( os.path.join( moduleDir, 'Resources', 'SpineScenes', "*.mrb" ) )
    for spine in spineScenes:
      slicer.util.loadScene( spine )'''

    # Build transform tree
    logging.debug('Set up transform tree')

    self.probeToReference.SetAndObserveTransformNodeID(self.referenceToRas.GetID())
    self.needleToReference.SetAndObserveTransformNodeID(self.referenceToRas.GetID())
    self.imageToProbe.SetAndObserveTransformNodeID(self.probeToReference.GetID())

    self.probeModelToProbe.SetAndObserveTransformNodeID(self.probeToReference.GetID())
    self.needleTipToNeedle.SetAndObserveTransformNodeID(self.needleToReference.GetID())

    self.ultrasound_flip.SetAndObserveTransformNodeID(self.probeModelToProbe.GetID())
    self.usProbeModel.SetAndObserveTransformNodeID(self.ultrasound_flip.GetID())
    self.needleModel.SetAndObserveTransformNodeID(self.needleTipToNeedle.GetID())
    
    self.ultrasound_Ultrasound.SetAndObserveTransformNodeID(self.imageToProbe.GetID())

    # Ensure that the sequence browser toolbar(s) is not made visible
    sequenceBrowserToolBars = slicer.util.mainWindow().findChildren( "qMRMLSequenceBrowserToolBar" )
    for toolBar in sequenceBrowserToolBars:
      toolBar.connect('visibilityChanged(bool)', partial( self.setSequenceBrowserToolBarsVisible, False ) )

    # Hide slice view annotations (patient name, scale, color bar, etc.) as they
    # decrease reslicing performance by 20%-100%
    logging.debug('Hide slice view annotations')
    import DataProbe
    dataProbeUtil=DataProbe.DataProbeLib.DataProbeUtil()
    dataProbeParameterNode=dataProbeUtil.getParameterNode()
    dataProbeParameterNode.SetParameter('showSliceViewAnnotations', '0')

    # Load and create the metrics
    metricsDirectory = os.path.join( moduleDir, os.pardir, os.pardir, "Metrics" )
    self.setupMetrics( metricsDirectory )

    
  def disconnect(self):#TODO see connect
    logging.debug('LumbarTutor.disconnect()')
    Guidelet.disconnect(self)
    # Inside disconnect(self):    
    self.compStep1Button.disconnect('clicked(bool)', self.onCompStep1Clicked)
    self.compStep2Button.disconnect('clicked(bool)', self.onCompStep2Clicked)
    self.compStep3Button.disconnect('clicked(bool)', self.onCompStep3Clicked)

    self.calibrationCollapsibleButton.disconnect('toggled(bool)', self.onCalibrationSetupPanelToggled)
    self.procedureCollapsibleButton.disconnect('toggled(bool)', self.onProcedureTabToggled)
    self.anatomyCollapsibleButton.disconnect('toggled(bool)', self.onAnatomyTabToggled)
    
    self.l3Button.disconnect('clicked(bool)', self.onL3Clicked)
    self.l4Button.disconnect('clicked(bool)', self.onL4Clicked)
    self.l5Button.disconnect('clicked(bool)', self.onL5Clicked)
    self.ligamentumButton.disconnect('clicked(bool)', self.onLigamentumClicked)
    self.spinalCordButton.disconnect('clicked(bool)', self.onSpinalCordClicked)
    
    self.insStep1Button.disconnect('clicked(bool)', self.onInsStep1Clicked)
    self.insStep2Button.disconnect('clicked(bool)', self.onInsStep2Clicked)
    self.insStep3Button.disconnect('clicked(bool)', self.onInsStep3Clicked)
    self.insStep4Button.disconnect('clicked(bool)', self.onInsStep4Clicked)
    
    self.fluidStep1Button.disconnect('clicked(bool)', self.onFluidStep1Clicked)
    self.fluidStep2Button.disconnect('clicked(bool)', self.onFluidStep2Clicked)
    self.fluidStep3Button.disconnect('clicked(bool)', self.onFluidStep3Clicked)
    self.fluidStep4Button.disconnect('clicked(bool)', self.onFluidStep4Clicked)
    
    self.pivotCalibrationButton.disconnect('clicked(bool)', self.onNeedleCalibrationClicked)
    self.spinCalibrationButton.disconnect('clicked(bool)', self.onSpinCalibrationClicked)
    self.pivotSamplingTimer.disconnect('timeout()', self.onPivotSamplingTimeout)
    
    self.viewAlignmentButton.disconnect('clicked(bool)', self.align3DView)
    
    self.step1Button.disconnect('clicked(bool)', self.onStep1Clicked)
    self.step2Button.disconnect('clicked(bool)', self.onStep2Clicked)
    self.step3Button.disconnect('clicked(bool)', self.onStep3Clicked)
    self.step4Button.disconnect('clicked(bool)', self.onStep4Clicked)
    self.step5Button.disconnect('clicked(bool)', self.onStep5Clicked)

    try:
      self.loadButton.disconnect('clicked()', self.onLoadButtonClicked)
      self.saveButton.disconnect('clicked()', self.saveAllRecordings)
      self.exitButton.disconnect('clicked()', self.onExitButtonClicked)
    except AttributeError:
      pass
    
    # Keyboard shortcuts
    self.startStopShortcutPlus.disconnect('activated()', self.ultrasound.startStopRecordingButton.click )
    try:
      self.advanceStepShortcut.disconnect('activated()', self.onAdvanceStepShortcut)
    except AttributeError:
      pass


  def onAnatomyTabToggled(self, toggled):
    if toggled:
      # Close all the other tabs
      self.calibrationCollapsibleButton.setProperty('collapsed', True)
      self.procedureCollapsibleButton.setProperty('collapsed', True)
  
  def onAdvanceStepShortcut(self):
    """Triggered when the user presses 'p'. Finds the active step and clicks it."""
    
    # --- Check if Anatomy Tab is open ---
    if not self.anatomyCollapsibleButton.collapsed:
      anatomyButtons = [
        self.l3Button, self.l4Button, self.l5Button, 
        self.ligamentumButton, self.spinalCordButton
      ]
      for btn in anatomyButtons:
        # Find the first button that is both visible and hasn't been clicked yet
        if btn.isVisible() and btn.isEnabled():
          btn.click() # Virtually click it!
          break # Stop after clicking one
          
    # --- Check if Procedure Tab is open ---
    elif not self.procedureCollapsibleButton.collapsed:
      procedureButtons = [
        self.step1Button, self.step2Button, self.step3Button, self.step4Button, self.step5Button,
        self.insStep1Button, self.insStep2Button, self.insStep3Button, self.insStep4Button,
        self.fluidStep1Button, self.fluidStep2Button, self.fluidStep3Button, self.fluidStep4Button,
        self.compStep1Button, self.compStep2Button, self.compStep3Button
      ]
      for btn in procedureButtons:
        if btn.isVisible() and btn.isEnabled():
          btn.click() # Virtually click it!
          break

  # --- Anatomy Click Logic ---
  def onL3Clicked(self):
    print("User is attempting to click L3...")
    # Add your 3D viewer interaction logic here
    self.advanceAnatomyStep(self.l3Button, self.l4Button)

  def onL4Clicked(self):
    print("User is attempting to click L4...")
    # Add your 3D viewer interaction logic here
    self.advanceAnatomyStep(self.l4Button, self.l5Button)

  def onL5Clicked(self):
    print("User is attempting to click L5...")
    # Add your 3D viewer interaction logic here
    self.advanceAnatomyStep(self.l5Button, self.ligamentumButton)
    
  def onLigamentumClicked(self):
    print("User is attempting to click Ligamentum Flavum...")
    # Add your 3D viewer interaction logic here
    self.advanceAnatomyStep(self.ligamentumButton, self.spinalCordButton)

  def onSpinalCordClicked(self):
    print("User is attempting to click Spinal Cord end...")
    # Add your 3D viewer interaction logic here
    self.advanceAnatomyStep(self.spinalCordButton, None)
    

  # ==========================================
  # PHASE 1 CLICK LOGIC
  # ==========================================
  def onStep1Clicked(self):
    self.advanceProcedureStep(self.step1Button, self.step2Button)

  def onStep2Clicked(self):
    self.advanceProcedureStep(self.step2Button, self.step3Button)

  def onStep3Clicked(self):
    self.advanceProcedureStep(self.step3Button, self.step4Button)
      
  def onStep4Clicked(self):
    self.advanceProcedureStep(self.step4Button, self.step5Button)

  def onStep5Clicked(self):
    # Transition to Needle Insertion phase
    self.advanceProcedureStep(self.step5Button, self.insStep1Button)

  # ==========================================
  # PHASE 2 CLICK LOGIC
  # ==========================================
  def onInsStep1Clicked(self):
    self.advanceProcedureStep(self.insStep1Button, self.insStep2Button)

  def onInsStep2Clicked(self):
    # NOTE: We use brackets [] here because this step reveals TWO buttons at once!
    self.advanceProcedureStep(self.insStep2Button, self.insStep3Button)

  def onInsStep3Clicked(self):
    self.advanceProcedureStep(self.insStep3Button, self.insStep4Button) # No new buttons reveal here

  def onInsStep4Clicked(self):
    # Transition to Fluid phase
    self.advanceProcedureStep(self.insStep4Button,self.fluidStep1Button)

  # ==========================================
  # PHASE 3 CLICK LOGIC
  # ==========================================
  def onFluidStep1Clicked(self):
    self.advanceProcedureStep(self.fluidStep1Button, self.fluidStep2Button)

  def onFluidStep2Clicked(self):
    self.advanceProcedureStep(self.fluidStep2Button, self.fluidStep3Button)

  def onFluidStep3Clicked(self):
    self.advanceProcedureStep(self.fluidStep3Button, self.fluidStep4Button)

  def onFluidStep4Clicked(self):
    # Transition to Completion phase
    self.advanceProcedureStep(self.fluidStep4Button, self.compStep1Button)

  # ==========================================
  # PHASE 4 CLICK LOGIC
  # ==========================================
  def onCompStep1Clicked(self):
    self.advanceProcedureStep(self.compStep1Button, self.compStep2Button)

  def onCompStep2Clicked(self):
    self.advanceProcedureStep(self.compStep2Button, self.compStep3Button)

  def onCompStep3Clicked(self):
    self.advanceProcedureStep(self.compStep3Button, None)

    
    if self.ultrasound.startStopRecordingButton.isChecked():
        self.ultrasound.startStopRecordingButton.click()

  def createPlusConnector(self, hostNamePort):
    connectorNode = slicer.vtkMRMLIGTLConnectorNode()
    #connectorNode.SetLogErrorIfServerConnectionFailed(False)
    slicer.mrmlScene.AddNode(connectorNode)
    [hostName, port] = hostNamePort.split(':')
    connectorNode.SetTypeClient(hostName, int(port))

    return connectorNode

    
  def setupTopPanel(self):
    buttonMinWidth = 48

    # 1. Create the layout
    self.topPanelLayout = qt.QGridLayout()

    # 2. CRITICAL FIX: Insert it at the very top of the main Guidelet panel (Index 0)
    self.sliceletPanelLayout.insertLayout(0, self.topPanelLayout)

    # 3. Load Button
    self.loadButton = qt.QPushButton()
    self.loadButton.setIcon(qt.QIcon(qt.QApplication.style().standardIcon(qt.QStyle.SP_DialogOpenButton)))
    self.loadButton.setMinimumWidth(buttonMinWidth)
    self.loadButton.toolTip = 'Load Volume'
    self.topPanelLayout.addWidget(self.loadButton, 0, 0)
    self.loadButton.connect('clicked()', self.onLoadButtonClicked)

    # 4. Save Button
    self.saveButton = qt.QPushButton()
    self.saveButton.setIcon(qt.QIcon(qt.QApplication.style().standardIcon(qt.QStyle.SP_DialogSaveButton)))
    self.saveButton.setMinimumWidth(buttonMinWidth)
    self.saveButton.toolTip = 'Save All Recordings'
    self.topPanelLayout.addWidget(self.saveButton, 0, 1)
    self.saveButton.connect('clicked()', self.saveAllRecordings)

    # 5. Exit Button
    self.exitButton = qt.QPushButton()
    self.exitButton.toolTip = 'Exit'
    self.exitButton.setMinimumWidth(buttonMinWidth)
    self.exitButton.setIcon(qt.QIcon(qt.QApplication.style().standardIcon(qt.QStyle.SP_BrowserStop)))
    self.topPanelLayout.addWidget(self.exitButton, 0, 2)
    self.exitButton.connect('clicked()', self.onExitButtonClicked)

    # Push the buttons to the left side
    self.topPanelLayout.setColumnStretch(3, 1)

  def onLoadButtonClicked(self):
    io = slicer.app.ioManager()
    params = {}
    io.openDialog("VolumeFile", slicer.qSlicerDataDialog.Read, params)

  def onExitButtonClicked(self):
    mainwindow = slicer.util.mainWindow()
    if mainwindow:
      mainwindow.close()

  def calibrationSetupPanel(self):
    logging.debug('calibrationSetupPanel')

    self.calibrationCollapsibleButton.setProperty('collapsedHeight', 20)
    self.calibrationCollapsibleButton.text = 'Calibration'
    self.sliceletPanelLayout.addWidget(self.calibrationCollapsibleButton)

    self.calibrationLayout = qt.QFormLayout(self.calibrationCollapsibleButton)
    self.calibrationLayout.setContentsMargins(12, 4, 4, 4)
    self.calibrationLayout.setSpacing(4)

    self.pivotCalibrationButton = qt.QPushButton("Pivot calibration")
    self.pivotCalibrationButton.setCheckable(False)
    self.calibrationLayout.addRow(self.pivotCalibrationButton)

    self.spinCalibrationButton = qt.QPushButton('Spin calibration')
    self.spinCalibrationButton.setCheckable(False)
    self.calibrationLayout.addRow(self.spinCalibrationButton)
    
    self.viewAlignmentButton = qt.QPushButton('3D View Alignment')
    self.viewAlignmentButton.setCheckable(False)
    self.calibrationLayout.addRow(self.viewAlignmentButton)
    
    self.countdownLabel = qt.QLabel()
    self.calibrationLayout.addRow(self.countdownLabel)

    self.pivotSamplingTimer = qt.QTimer()
    self.pivotSamplingTimer.setInterval(500)
    self.pivotSamplingTimer.setSingleShot(True)
    
    self.isSpinCalibration = False


  def onNeedleCalibrationClicked(self, toggled):
    logging.debug('onNeedleCalibrationClicked')
    self.pivotCalibrationButton.setEnabled(False)
    self.spinCalibrationButton.setEnabled(False)

    self.isSpinCalibration = False

    self.pivotCalibrationLogic.SetAndObserveTransformNode(self.needleToReference)
    self.pivotCalibrationStopTime = time.time() + 5.0  
    self.pivotCalibrationLogic.SetRecordingState(True)
    self.onPivotSamplingTimeout()


  def onPivotSamplingTimeout(self):
    self.countdownLabel.setText("Pivot calibrating for {0:.0f} more seconds".format(self.pivotCalibrationStopTime-time.time()))
    if(time.time()<self.pivotCalibrationStopTime):
      # continue
      self.pivotSamplingTimer.start()
    else:
      # calibration completed
      self.onStopPivotCalibration()


  def onSpinCalibrationClicked(self, toggled):
    logging.debug('onSpineCalibrationClicked')
    self.spinCalibrationButton.setEnabled(False)
    self.pivotCalibrationButton.setEnabled(False)

    self.isSpinCalibration = True

    self.pivotCalibrationLogic.SetAndObserveTransformNode(self.needleToReference)
    self.pivotCalibrationStopTime = time.time() + 5.0
    self.pivotCalibrationLogic.SetRecordingState(True)
    self.onPivotSamplingTimeout()


  def onStopPivotCalibration(self):
    self.pivotCalibrationLogic.SetRecordingState(False)
    self.pivotCalibrationButton.setEnabled(True)
    self.spinCalibrationButton.setEnabled(True)

    if self.isSpinCalibration == False:
      self.pivotCalibration()
    else:
      self.spinCalibration()

  def pivotCalibration(self):
    calibrationSuccess = self.pivotCalibrationLogic.ComputePivotCalibration()
    if not calibrationSuccess:
      self.countdownLabel.setText("Calibration failed: " + self.pivotCalibrationLogic.GetErrorText())
      self.pivotCalibrationLogic.ClearToolToReferenceMatrices()
      return
    if(self.pivotCalibrationLogic.GetPivotRMSE() >= 1.2):  # TODO: Make this a node paramter
      self.countdownLabel.setText("Calibration failed, error = {0:.2f} mm, please calibrate again!".format(self.pivotCalibrationLogic.GetPivotRMSE()))
      self.pivotCalibrationLogic.ClearToolToReferenceMatrices()
      return
    tooltipToToolMatrix = vtk.vtkMatrix4x4()
    self.pivotCalibrationLogic.GetToolTipToToolMatrix(tooltipToToolMatrix)
    self.pivotCalibrationLogic.ClearToolToReferenceMatrices()
    self.needleTipToNeedle.SetMatrixTransformToParent(tooltipToToolMatrix)
    self.logic.writeTransformToSettings('NeedleTipToNeedle', tooltipToToolMatrix, self.configurationName)
    self.countdownLabel.setText("Calibration completed, error = {0:.2f} mm".format(self.pivotCalibrationLogic.GetPivotRMSE()))
    logging.debug("Pivot calibration completed. RMSE = {0:.2f} mm".format(self.pivotCalibrationLogic.GetPivotRMSE()))


  def spinCalibration(self):
    logging.debug('spinCalibration')
    calibrationSuccess = self.pivotCalibrationLogic.ComputeSpinCalibration()
    if not calibrationSuccess:
      self.countdownLabel.setText("Calibration failed: " + self.pivotCalibrationLogic.GetErrorText())
      self.pivotCalibrationLogic.ClearToolToReferenceMatrices()
      return
    if (self.pivotCalibrationLogic.GetSpinRMSE() >= 0.1):  # TODO: Make this a node parameter
      self.countdownLabel.setText("Calibration error too high!: {0:.3f}, please calibrate again!".format(
        self.pivotCalibrationLogic.GetSpinRMSE()))
      self.pivotCalibrationLogic.ClearToolToReferenceMatrices()
      return
    needleTipToNeedleMatrix = vtk.vtkMatrix4x4()
    needleTipToNeedleRotationMatrix = vtk.vtkMatrix4x4()
    self.needleTipToNeedle.GetMatrixTransformToParent(needleTipToNeedleMatrix)
    needleTipToNeedleMatrixTranslation = vtk.vtkMatrix4x4()
    needleTipToNeedleMatrixTranslation.SetElement(0, 3, needleTipToNeedleMatrix.GetElement(0, 3))
    needleTipToNeedleMatrixTranslation.SetElement(1, 3, needleTipToNeedleMatrix.GetElement(1, 3))
    needleTipToNeedleMatrixTranslation.SetElement(2, 3, needleTipToNeedleMatrix.GetElement(2, 3))
    self.pivotCalibrationLogic.GetToolTipToToolRotation(needleTipToNeedleRotationMatrix)
    vtk.vtkMatrix4x4().Multiply4x4(needleTipToNeedleMatrixTranslation, needleTipToNeedleRotationMatrix, needleTipToNeedleMatrix)
    self.needleTipToNeedle.SetMatrixTransformToParent(needleTipToNeedleMatrix)
    self.pivotCalibrationLogic.ClearToolToReferenceMatrices()
    self.logic.writeTransformToSettings('NeedleTipToNeedle', needleTipToNeedleMatrix, self.configurationName)
    self.countdownLabel.setText('Calibration completed.')
    logging.debug('Spin calibration completed. RMSE = {0:.3f} mm'.format(self.pivotCalibrationLogic.GetSpinRMSE()))

    
  def align3DView(self):
    # We want a view from the posterior with the superior up and the left left
    # The spine should be centred
    spineCenter_RAS = [ 0, 0, 0 ]
    if ( self.spineModel is not None ):
      comFilter = vtk.vtkCenterOfMass()
      comFilter.SetInputData( self.spineModel.GetPolyData() )
      comFilter.SetUseScalarsAsWeights( False )
      comFilter.Update()
      spineCenter_RAS = comFilter.GetCenter()
      
    # Setup the cameras for the 3D views
    # Implicit assumption that the spine is rotationally aligned with the RAS coordinate frame
    CAMERA_DISTANCE = 600 #mm # Controls the "zoom"
    CAMERA_CLIPPING_RANGE = [ 0.1, 1000 ] # This is the default clipping range. Change it if you change the camera distance.
    cameraNodes = slicer.mrmlScene.GetNodesByClass( "vtkMRMLCameraNode" )
    if ( cameraNodes.GetNumberOfItems() > 0 ):
      camera0 = cameraNodes.GetItemAsObject( 0 )
      camera0.SetFocalPoint( spineCenter_RAS[ 0 ], spineCenter_RAS[ 1 ] - 50, spineCenter_RAS[ 2 ] )
      camera0.SetPosition( spineCenter_RAS[ 0 ] - CAMERA_DISTANCE, spineCenter_RAS[ 1 ] - 50, spineCenter_RAS[ 2 ] )
      camera0.SetViewUp( 0, 0, 1 )
      camera0.GetCamera().SetClippingRange( CAMERA_CLIPPING_RANGE )      
    

  def addSnapshotsToUltrasoundPanel(self):
    self.ultrasoundCollapsibleButton.text = "Ultrasound"

    # Snapshots
    self.ultrasoundSnapshotButton = qt.QPushButton("Ultrasound snapshot")
    self.ultrasoundLayout.addRow(self.ultrasoundSnapshotButton)

    self.clearSnapshotsButton = qt.QPushButton('Clear ultrasound snapshots')
    self.ultrasoundLayout.addRow(self.clearSnapshotsButton)
    
    
  def addSpineSelectionToUltrasoundPanel(self):
    self.spineComboBox = slicer.qMRMLNodeComboBox()
    self.spineComboBox.nodeTypes = ["vtkMRMLModelNode"]
    self.spineComboBox.noneEnabled = True
    self.spineComboBox.removeEnabled = False
    self.spineComboBox.addEnabled = False
    self.spineComboBox.renameEnabled = False
    self.spineComboBox.setMRMLScene(slicer.mrmlScene)
    self.spineComboBox.sortFilterProxyModel().addAttribute( "vtkMRMLModelNode", "SpineModel" )
    self.ultrasoundLayout.addRow(self.spineComboBox)


  def addRecordingsTableToUltrasoundPanel(self):
    self.recordingsTable = qt.QTableWidget()
    self.recordingsTable.setRowCount(0)
    self.recordingsTable.setColumnCount(2)
    self.recordingsTable.horizontalHeader().setSectionResizeMode(0, qt.QHeaderView.Stretch)
    self.recordingsTable.setHorizontalHeaderLabels( [ "Recording name", "Delete" ] )
    
    self.saveRecordingsButton = qt.QPushButton()
    self.saveRecordingsButton.setText( "Save all recordings" )
    self.saveRecordingsButton.setIcon( slicer.app.style().standardIcon(qt.QStyle.SP_DialogSaveButton) )
    
    self.ultrasoundLayout.addRow(qt.QLabel()) # Blank row for spacing between table and buttons.
    self.ultrasoundLayout.addRow(self.recordingsTable)
    self.ultrasoundLayout.addRow(self.saveRecordingsButton)


  def updateRecordingsTable(self, observer, eventid):
    # Disconnect the cell changed signal to prevent key errors
    self.recordingsTable.disconnect('cellChanged(int, int)', self.updateSequenceBrowserNodeName)

    numberOfNodes = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLSequenceBrowserNode")
    self.recordingsTable.setRowCount(numberOfNodes)
    self.sequenceBrowserNodeDict = {} # Keys are the row number in the table

    # If a change has been made to the scene with a new sequence browser node,
    # update the table, displaying the name of the node as well as a delete button
    # for that node. The connection is handled by the partial function that links
    # a unique removeSequenceBrowserNodeFromScene function with the generated button.
    for nodeNumber in range(numberOfNodes):
      aSequenceBrowserNode = slicer.mrmlScene.GetNthNodeByClass(nodeNumber,"vtkMRMLSequenceBrowserNode")
      recordingsTableItem = qt.QTableWidgetItem(aSequenceBrowserNode.GetName())
      deleteRecordingsTableButton = qt.QPushButton()
      deleteRecordingsTableButton.setIcon( slicer.app.style().standardIcon(qt.QStyle.SP_DialogDiscardButton) )
      deleteRecordingsTableButton.connect('clicked()', partial(self.removeSequenceBrowserNodeFromScene, nodeNumber))

      # Update the dictionary of sequence browser nodes with the new node
      self.sequenceBrowserNodeDict[nodeNumber] = aSequenceBrowserNode

      # Add items to the table
      self.recordingsTable.setItem(nodeNumber, 0, recordingsTableItem)
      self.recordingsTable.setCellWidget(nodeNumber, 1, deleteRecordingsTableButton)

    # Reconnect the cell changed signal
    self.recordingsTable.connect('cellChanged(int, int)', self.updateSequenceBrowserNodeName)


  def updateSequenceBrowserNodeName(self, row, col):
    newName = self.recordingsTable.item(row,col).text()
    self.sequenceBrowserNodeDict[row].SetName(newName)


  def removeSequenceBrowserNodeFromScene(self, row):
    # Get the list of synched sequence nodes from a selected sequence browser node for deletion
    browserNodeToDelete = self.sequenceBrowserNodeDict[row]

    syncedSequenceNodes = vtk.vtkCollection()
    browserNodeToDelete.GetSynchronizedSequenceNodes(syncedSequenceNodes, True)

    virtualOutputNodes = vtk.vtkCollection()
    browserNodeToDelete.GetAllVirtualOutputDataNodes(virtualOutputNodes)

    slicer.mrmlScene.RemoveNode(browserNodeToDelete) # Do this first, otherwise, it will remove all the virtual data nodes from the scene

    # Iterate through the synced sequence nodes to remove both them from the scene
    for nodeIndex in range (syncedSequenceNodes.GetNumberOfItems()):
      syncedSequenceNode = syncedSequenceNodes.GetItemAsObject(nodeIndex)
      slicer.mrmlScene.RemoveNode(syncedSequenceNode)

    # Iterate through the virtual output nodes to remove both them from the scene
    for nodeIndex in range (virtualOutputNodes.GetNumberOfItems()):
      virtualOutputNode = virtualOutputNodes.GetItemAsObject(nodeIndex)
      #slicer.mrmlScene.RemoveNode(virtualOutputNode) # Do not remove from scene, so the transform hierarchy is maintained


  def saveAllRecordings(self):
    savedScenesDirectory = self.parameterNode.GetParameter('SavedScenesDirectory')
    if ( not os.path.exists(savedScenesDirectory) ):
      os.makedirs(savedScenesDirectory) # Make the directory if it doesn't already exist
    
    recordingCollection = slicer.mrmlScene.GetNodesByClass( "vtkMRMLSequenceBrowserNode" )
    for nodeNumber in range( recordingCollection.GetNumberOfItems() ):
      browserNode = recordingCollection.GetItemAsObject( nodeNumber )
      filename = browserNode.GetName() + "-" + time.strftime("%Y%m%d-%H%M%S") + os.extsep + "sqbr"
      filename = os.path.join( savedScenesDirectory, filename )
      slicer.util.saveNode( browserNode, filename )


  def setupAnatomyPanel(self):
      import logging
      logging.debug('setupAnatomyPanel')

      self.anatomyCollapsibleButton = ctk.ctkCollapsibleButton()
      self.anatomyCollapsibleButton.setProperty('collapsedHeight', 20)
      self.anatomyCollapsibleButton.text = "Anatomy"
      self.anatomyCollapsibleButton.setMinimumWidth(380) # Match the width of the Procedure tab
      self.sliceletPanelLayout.addWidget(self.anatomyCollapsibleButton)

      # Set up the Scroll Area
      self.anatomyCollapsibleLayout = qt.QVBoxLayout(self.anatomyCollapsibleButton)
      self.anatomyCollapsibleLayout.setContentsMargins(0, 0, 0, 0)
      
      self.anatomyScrollArea = qt.QScrollArea()
      self.anatomyScrollArea.setWidgetResizable(True)
      self.anatomyScrollArea.setFrameShape(qt.QFrame.NoFrame)
      self.anatomyScrollArea.setVerticalScrollBarPolicy(qt.Qt.ScrollBarAlwaysOn)
      self.anatomyScrollArea.setHorizontalScrollBarPolicy(qt.Qt.ScrollBarAlwaysOff)
      self.anatomyCollapsibleLayout.addWidget(self.anatomyScrollArea)

      self.anatomyContainerWidget = qt.QWidget()
      self.anatomyScrollArea.setWidget(self.anatomyContainerWidget)

      self.anatomyLayout = qt.QVBoxLayout(self.anatomyContainerWidget)
      self.anatomyLayout.setContentsMargins(12, 4, 4, 4)
      self.anatomyLayout.setSpacing(4)

      # --- BUTTON 1: L3 (Visible initially) ---
      self.l3Button = self.createWrappedButton("Click the L3")
      self.anatomyLayout.addWidget(self.l3Button)

      # --- BUTTON 2: L4 (Hidden initially) ---
      self.l4Button = self.createWrappedButton("Click the L4")
      self.l4Button.setVisible(False)
      self.anatomyLayout.addWidget(self.l4Button)

      # --- BUTTON 3: L5 (Hidden initially) ---
      self.l5Button = self.createWrappedButton("Click the L5")
      self.l5Button.setVisible(False)
      self.anatomyLayout.addWidget(self.l5Button)

      # --- BUTTON 4: Ligamentum Flavum (Hidden initially) ---
      self.ligamentumButton = self.createWrappedButton("Click the Ligamentum Flavum")
      self.ligamentumButton.setVisible(False)
      self.anatomyLayout.addWidget(self.ligamentumButton)

      # --- BUTTON 5: Spinal Cord (Hidden initially) ---
      self.spinalCordButton = self.createWrappedButton("Click where the solid spinal cord ends")
      self.spinalCordButton.setVisible(False)
      self.anatomyLayout.addWidget(self.spinalCordButton)
      
      self.anatomyLayout.addStretch(1)
  
  def createWrappedButton(self, text):
    # 1. Create a pure, native C++ QPushButton so Slicer styles it perfectly!
    btn = qt.QPushButton()
    btn.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.MinimumExpanding)
    
    # 2. Create the transparent, word-wrapping label
    label = qt.QLabel(text)
    label.setWordWrap(True)
    label.setAlignment(qt.Qt.AlignCenter)
    label.setAttribute(qt.Qt.WA_TransparentForMouseEvents)
    # Inherit text color so it changes dynamically in dark/light mode
    label.setStyleSheet("background-color: transparent; color: inherit;") 
    
    # 3. Add the label inside the button
    btnLayout = qt.QVBoxLayout(btn)
    btnLayout.setContentsMargins(8, 8, 8, 8)
    btnLayout.addWidget(label)
    return btn
  
  def advanceProcedureStep(self, currentButton, nextButtons=None):
    """Disables current step, reveals next step(s), and auto-scrolls to the bottom."""
    # 1. Disable the current button (locks it in place without changing its text)
    currentButton.setEnabled(False)
    
    # 2. Reveal the next button(s)
    if nextButtons is not None:
      # This allows the function to handle a single button OR a list of multiple buttons
      if not isinstance(nextButtons, list):
        nextButtons = [nextButtons]
      for btn in nextButtons:
        btn.setVisible(True)
        
    # 3. Force Slicer to instantly calculate the new height of the Procedure tab
    slicer.app.processEvents()
    
    # 4. Auto-scroll to the absolute bottom to push the previous steps up!
    scrollBar = self.procedureScrollArea.verticalScrollBar()
    scrollBar.setValue(scrollBar.maximum)
  
  def advanceAnatomyStep(self, currentButton, nextButtons=None):
    """Disables current Anatomy step, reveals next step(s), and auto-scrolls to the bottom."""
    currentButton.setEnabled(False)
    
    if nextButtons is not None:
      if not isinstance(nextButtons, list):
        nextButtons = [nextButtons]
      for btn in nextButtons:
        btn.setVisible(True)
        
    slicer.app.processEvents()
    
    # Auto-scroll to the bottom of the Anatomy tab
    scrollBar = self.anatomyScrollArea.verticalScrollBar()
    scrollBar.setValue(scrollBar.maximum)

  def setupProcedurePanel(self):
    import logging
    logging.debug('setupProcedurePanel')

    self.procedureCollapsibleButton.setProperty('collapsedHeight', 20)
    self.procedureCollapsibleButton.text = "Procedure"
    self.sliceletPanelLayout.addWidget(self.procedureCollapsibleButton)

    self.procedureCollapsibleLayout = qt.QVBoxLayout(self.procedureCollapsibleButton)
    self.procedureCollapsibleLayout.setContentsMargins(0, 0, 0, 0)
    
    self.procedureScrollArea = qt.QScrollArea()
    self.procedureScrollArea.setWidgetResizable(True) 
    self.procedureScrollArea.setFrameShape(qt.QFrame.NoFrame)
    self.procedureScrollArea.setVerticalScrollBarPolicy(qt.Qt.ScrollBarAlwaysOn)   # Forces scrollbar to always show
    self.procedureScrollArea.setHorizontalScrollBarPolicy(qt.Qt.ScrollBarAlwaysOff) # Prevents bottom scrollbar
    self.procedureCollapsibleButton.setMinimumWidth(380) # Makes the tab wider (adjust the 380 if you want it wider/narrower)
    self.procedureCollapsibleLayout.addWidget(self.procedureScrollArea)

    self.procedureContainerWidget = qt.QWidget()
    self.procedureScrollArea.setWidget(self.procedureContainerWidget)

    self.procedureLayout = qt.QVBoxLayout(self.procedureContainerWidget)
    self.procedureLayout.setContentsMargins(12, 4, 4, 4)
    self.procedureLayout.setSpacing(4)

    # ==========================================
    # PHASE 1: PRE-PROCEDURE
    # ==========================================
    self.step1Button = self.createWrappedButton("Before Begining, the patient should be positioned in the lateral decubitus position or upright leaning forward withtheir feet supported, with their back facing the clinician. The patient's hips and knees should be flexed to open up the spaces between the vertebrae.")
    self.procedureLayout.addWidget(self.step1Button)

    self.step2Button = self.createWrappedButton("Palpate the iliac crests and spinous processes L3, L4, L5")
    self.step2Button.setVisible(False) 
    self.procedureLayout.addWidget(self.step2Button)

    self.step3Button = self.createWrappedButton("Palpate the L4/L5 interspace, specifically at the midline")
    self.step3Button.setVisible(False) 
    self.procedureLayout.addWidget(self.step3Button)

    self.step4Button = self.createWrappedButton("Mark that spot with a marker or pen")
    self.step4Button.setVisible(False) 
    self.procedureLayout.addWidget(self.step4Button)

    self.step5Button = self.createWrappedButton("Wash hands, apply gloves, drape the patient, and prepare the tools")
    self.step5Button.setVisible(False) 
    self.procedureLayout.addWidget(self.step5Button)

    # ==========================================
    # PHASE 2: NEEDLE INSERTION
    # ==========================================
    self.insStep1Button = self.createWrappedButton("Sterilize the field")
    self.insStep1Button.setVisible(False) 
    self.procedureLayout.addWidget(self.insStep1Button)

    self.insStep2Button = self.createWrappedButton("Inject idocane at the site of the procedure (subcutaneous injection)")
    self.insStep2Button.setVisible(False) 
    self.procedureLayout.addWidget(self.insStep2Button)

    self.insStep3Button = self.createWrappedButton("With the stylet in place, insert the needle slowly at the midline (and parallel to it) above the lower spinus process with and angle of 15-20 degrees cephalad")
    self.insStep3Button.setVisible(False) 
    self.procedureLayout.addWidget(self.insStep3Button)

    self.insStep4Button = self.createWrappedButton("Feel for a loss of resistance or pop sensation as the needle passes the ligamentum flavum and enters the epidural space \n Note: if you hit bone, move back a few millimeters and try again.")
    self.insStep4Button.setVisible(False) 
    self.procedureLayout.addWidget(self.insStep4Button)

    # ==========================================
    # PHASE 3: FLUID REMOVAL
    # ==========================================
    self.fluidStep1Button = self.createWrappedButton("Remove the stylet and note any fluid that appears at the end of the needle \n Note: if no fluid is appearing, place the stylet back in and move slightly forward (3-5 mm deeper) and repeat the process")
    self.fluidStep1Button.setVisible(False) 
    self.procedureLayout.addWidget(self.fluidStep1Button)

    self.fluidStep2Button = self.createWrappedButton("Once fluid is collected, reinsert the stylet")
    self.fluidStep2Button.setVisible(False)
    self.procedureLayout.addWidget(self.fluidStep2Button)

    self.fluidStep3Button = self.createWrappedButton("Remove the needle slowly") 
    self.fluidStep3Button.setVisible(False) 
    self.procedureLayout.addWidget(self.fluidStep3Button)

    self.fluidStep4Button = self.createWrappedButton("Apply pressure to the site and bandage the wound")
    self.fluidStep4Button.setVisible(False) 
    self.procedureLayout.addWidget(self.fluidStep4Button)

    # ==========================================
    # PHASE 4: PROCEDURE COMPLETION
    # ==========================================
    self.compStep1Button = self.createWrappedButton("Dispose of the needle in the sharps container")
    self.compStep1Button.setVisible(False) 
    self.procedureLayout.addWidget(self.compStep1Button)

    self.compStep2Button = self.createWrappedButton("Clean up the field and remove drapes")
    self.compStep2Button.setVisible(False) 
    self.procedureLayout.addWidget(self.compStep2Button)

    self.compStep3Button = self.createWrappedButton("End of Study")
    self.compStep3Button.setVisible(False) 
    self.procedureLayout.addWidget(self.compStep3Button)
    
    self.procedureLayout.addStretch(1)

  def setupResultsPanel(self):
    logging.debug('setupResultsPanel')

    self.resultsCollapsibleButton.setProperty('collapsedHeight', 20)
    self.resultsCollapsibleButton.text = "Results"
    self.sliceletPanelLayout.addWidget(self.resultsCollapsibleButton)

    self.resultsCollapsibleLayout = qt.QVBoxLayout(self.resultsCollapsibleButton)
    self.resultsCollapsibleLayout.setContentsMargins(12, 4, 4, 4)
    self.resultsCollapsibleLayout.setSpacing(4)

    self.resultsControlsLayout = qt.QFormLayout(self.resultsCollapsibleButton)
    self.resultsCollapsibleLayout.addLayout(self.resultsControlsLayout)

    self.recordingComboBox = slicer.qMRMLNodeComboBox()
    self.recordingComboBox.nodeTypes = ["vtkMRMLSequenceBrowserNode"]
    self.recordingComboBox.removeEnabled = False
    self.recordingComboBox.addEnabled = False
    self.recordingComboBox.renameEnabled = False
    self.recordingComboBox.setMRMLScene(slicer.mrmlScene)
    self.resultsControlsLayout.addRow("Select recording: ",self.recordingComboBox)
    self.recordingComboBox.connect('currentNodeChanged(bool)',self.onRecordingNodeSelected)

    self.recordingPlayWidget = slicer.qMRMLSequenceBrowserPlayWidget()
    self.resultsControlsLayout.addRow(self.recordingPlayWidget)

    self.calculateMetricsButton = qt.QPushButton("Calculate metrics")
    self.resultsControlsLayout.addRow(self.calculateMetricsButton)
    self.calculateMetricsButton.connect('clicked(bool)', self.onCalculateMetricsButtonClicked)

    self.metricsTableWidget = slicer.qSlicerMetricsTableWidget()
    self.metricsTableWidget.setExpandHeightToContents(False)
    self.metricsTableWidget.setShowMetricRoles(True)
    self.metricsTableWidget.setMRMLScene(slicer.mrmlScene)
    self.metricsTableWidget.setMetricsTableSelectionRowVisible( False )
    self.resultsCollapsibleLayout.addWidget(qt.QLabel()) # Blank row for spacing between table and buttons.
    self.resultsCollapsibleLayout.addWidget(self.metricsTableWidget)
    self.resultsCollapsibleLayout.addWidget(qt.QLabel()) # Blank row for spacing between table and buttons.
    
    self.captureVideoButton = qt.QPushButton( "Capture video" )
    self.resultsControlsLayout.addRow(self.captureVideoButton)
    self.captureVideoButton.connect('clicked(bool)', self.onCaptureVideoButtonClicked)


  def onRecordingNodeSelected(self):
    selectedNode = self.recordingComboBox.currentNode()
    self.stopSequenceBrowserPlayback()
    self.setPlaybackRealtime(selectedNode)
    self.recordingPlayWidget.setMRMLSequenceBrowserNode(selectedNode)


  def setupMetrics(self, metricsDirectory):
    # Import all of the metric scripts and create the metric instances
    peLogic = slicer.modules.perkevaluator.logic()
    if (peLogic is None):
      logging.error( "LumbarTutorLogic::setupMetrics could not find Perk Evaluator logic." )
      return

    self.perkEvaluatorNode = slicer.vtkMRMLPerkEvaluatorNode()
    self.perkEvaluatorNode.SetScene(slicer.mrmlScene)
    slicer.mrmlScene.AddNode(self.perkEvaluatorNode)

    self.metricsTableNode = slicer.vtkMRMLTableNode()
    self.metricsTableNode.SetScene(slicer.mrmlScene)
    slicer.mrmlScene.AddNode(self.metricsTableNode)

    self.perkEvaluatorNode.SetMetricsTableID( self.metricsTableNode.GetID() )
    # These metrics are all shared
    # No need to create an instance - an instance is already created automatically
    # TODO: This behaviour may be changed. Metrics will eventually be non-shared by default.

    # Remove all pervasive metric instances and just recreate the ones for the relevant transforms
    metricInstanceNodes = slicer.mrmlScene.GetNodesByClass( "vtkMRMLMetricInstanceNode" )
    for i in range( metricInstanceNodes.GetNumberOfItems() ):
      node = metricInstanceNodes.GetItemAsObject( i )
      pervasive = peLogic.GetMetricPervasive( node.GetAssociatedMetricScriptID() )
      needleTipRole = node.GetRoleID( "Any", slicer.vtkMRMLMetricInstanceNode.TransformRole ) == self.needleTipToNeedle.GetID()
      probeRole = node.GetRoleID( "Any", slicer.vtkMRMLMetricInstanceNode.TransformRole ) == self.probeToReference.GetID()
      if ( pervasive and not needleTipRole and not probeRole ):
        self.perkEvaluatorNode.RemoveMetricInstanceID( node.GetID() )


    # Generic needle-plane distance/angle computation
    needlePlaneDistanceAngleScript = slicer.util.loadNodeFromFile( os.path.join( metricsDirectory, "NeedlePlaneDistanceAngle.py" ), "Python Metric Script", {})

    # Generic in-action computation
    inActionScript = slicer.util.loadNodeFromFile( os.path.join( metricsDirectory, "InAction.py" ), "Python Metric Script", {})

    # Max/average needle-tip to ultrasound plane distance/angle
    maximumNeedlePlaneDistanceScript = slicer.util.loadNodeFromFile( os.path.join( metricsDirectory, "MaximumNeedlePlaneDistance.py" ), "Python Metric Script", {})
    averageNeedlePlaneDistanceScript = slicer.util.loadNodeFromFile( os.path.join( metricsDirectory, "AverageNeedlePlaneDistance.py" ), "Python Metric Script", {})
    maximumNeedlePlaneAngleScript = slicer.util.loadNodeFromFile( os.path.join( metricsDirectory, "MaximumNeedlePlaneAngle.py" ), "Python Metric Script", {})
    averageNeedlePlaneAngleScript = slicer.util.loadNodeFromFile( os.path.join( metricsDirectory, "AverageNeedlePlaneAngle.py" ), "Python Metric Script", {})

    # Everything should be OK with the same roles
    peLogic.SetMetricInstancesRolesToID( self.perkEvaluatorNode, self.needleTipToNeedle.GetID(), "Needle", slicer.vtkMRMLMetricInstanceNode.TransformRole )
    peLogic.SetMetricInstancesRolesToID( self.perkEvaluatorNode, self.imageToProbe.GetID(), "Ultrasound", slicer.vtkMRMLMetricInstanceNode.TransformRole )
    peLogic.SetMetricInstancesRolesToID( self.perkEvaluatorNode, self.tissueModel.GetID(), "Tissue", slicer.vtkMRMLMetricInstanceNode.AnatomyRole )
    peLogic.SetMetricInstancesRolesToID( self.perkEvaluatorNode, self.metricsTableNode.GetID(), "Parameter", slicer.vtkMRMLMetricInstanceNode.AnatomyRole )


  def onCalculateMetricsButtonClicked(self):
    sequenceBrowserNode = self.recordingComboBox.currentNode()
    self.perkEvaluatorNode.SetTrackedSequenceBrowserNodeID( sequenceBrowserNode.GetID() )

    peLogic = slicer.modules.perkevaluator.logic()
    if (peLogic is None):
      logging.error( "LumbarTutorLogic::onCalculateMetricsButtonClicked could not find Perk Evaluator logic." )
      return

    peLogic.ComputeMetrics(self.perkEvaluatorNode)
    
    
  def onCaptureVideoButtonClicked(self):
    sequenceBrowserNode = self.recordingComboBox.currentNode()
    masterSequenceNode = sequenceBrowserNode.GetMasterSequenceNode()

    try:
      import ScreenCapture
      scLogic = ScreenCapture.ScreenCaptureLogic()
    except:
      logging.error( "LumbarTutorLogic::onCaptureVideoButtonClicked could not find Screen Capture logic." )
      return
      
    try:
      threeDViewNode = slicer.app.layoutManager().threeDWidget( 0 ).threeDView().mrmlViewNode()
    except:
      logging.error( "LumbarTutorLogic::onCaptureVideoButtonClicked could not find 3D view node Capture logic." )
      return
    
    sequenceBrowserNode.Modified() # Force update the images
    # Make some adjustments to the views
    self.ultrasound_Ultrasound.GetDisplayNode().SetAutoWindowLevel( 0 )
    self.ultrasound_Ultrasound.GetDisplayNode().SetWindowLevelMinMax( 0, 120 )
    self.webcam_Webcam.GetDisplayNode().SetAutoWindowLevel( 0 )
    self.webcam_Webcam.GetDisplayNode().SetWindowLevelMinMax( 0, 256 )
    # These aren't strictly necessary, but nice to confirm
    self.displayImageInSliceViewer(self.ultrasound_Ultrasound.GetID(), "Red", False, 180)
    self.displayImageInSliceViewer(self.webcam_Webcam.GetID(), "Yellow", True, 0)
    
    # Parameters for capturing    
    startIndex = 0
    endIndex = masterSequenceNode.GetNumberOfDataNodes()
    steps = endIndex - startIndex
    outputDir = self.parameterNode.GetParameter('SavedScenesDirectory')
    imageFileNamePattern = scLogic.getRandomFilePattern()
    captureAllViews = True

    # Parameters for conversion to video
    fps = steps / ( float( masterSequenceNode.GetNthIndexValue( steps - 1 ) ) - float( masterSequenceNode.GetNthIndexValue( 0 ) ) )
    videoFormat = scLogic.videoFormatPresets[ 2 ][ "extraVideoOptions" ] # mpeg format
    videoName = sequenceBrowserNode.GetName() + ".mp4"

    # Capture and create the video
    scLogic.captureSequence( threeDViewNode, sequenceBrowserNode, startIndex, endIndex, steps, outputDir, imageFileNamePattern, captureAllViews )
    scLogic.createVideo( fps, videoFormat, outputDir, imageFileNamePattern, videoName )
    scLogic.deleteTemporaryFiles( outputDir, imageFileNamePattern, steps )


  def onCalibrationSetupPanelToggled(self, toggled):
    if toggled == False:
      return

    logging.debug('onCalibrationSetupPanelToggled: {0}'.format(toggled))
    self.navigationView = self.parameterNode.GetParameter( "CalibrationLayout" )
    self.updateNavigationView()


  def onUltrasoundPanelToggled(self, toggled):
    logging.debug('onUltrasoundPanelToggled: {0}'.format(toggled))
    self.navigationView = self.parameterNode.GetParameter( "ProcedureLayout" )
    self.updateNavigationView()

    # The user may want to freeze the image (disconnect) to make contouring easier.
    # Disable automatic ultrasound image auto-fit when the user unfreezes (connect)
    # to avoid zooming out of the image.
    self.fitUltrasoundImageToViewOnConnect = not toggled

  def onProcedureTabToggled(self, toggled):
    if toggled:
      # Close all the other tabs
      self.calibrationCollapsibleButton.setProperty('collapsed', True)
      self.anatomyCollapsibleButton.setProperty('collapsed', True) 
    
  def onSpineSelected(self):
    selectedSpineModel = self.spineComboBox.currentNode()
    selectedTissueModel = None
    selectedReferenceToRas = None
    if ( selectedSpineModel is not None ):
      selectedTissueModel = selectedSpineModel.GetNodeReference( "LumbarTutor.TissueModel" )
      selectedReferenceToRas = selectedSpineModel.GetNodeReference( "LumbarTutor.ReferenceToRAS" )
      
    if ( selectedSpineModel is None ):
      self.spineModel.SetAndObservePolyData( vtk.vtkPolyData() )
    else:
      self.spineModel.SetAndObservePolyData( selectedSpineModel.GetPolyData() )
      
    if ( selectedTissueModel is None ):
      self.tissueModel.SetAndObservePolyData( vtk.vtkPolyData() )
    else:
      self.tissueModel.SetAndObservePolyData( selectedTissueModel.GetPolyData() )
      
    if ( selectedReferenceToRas is None ):
      self.referenceToRas.SetMatrixTransformToParent( vtk.vtkMatrix4x4() )
    else:
      self.referenceToRas.SetMatrixTransformToParent( selectedReferenceToRas.GetMatrixTransformToParent() )

    self.align3DView()      
    

  def getCamera(self, viewName):
    """
    Get camera for the selected 3D view
    """
    camerasLogic = slicer.modules.cameras.logic()
    camera = camerasLogic.GetViewActiveCameraNode(slicer.util.getNode(viewName))
    return camera


  def getViewNode(self, viewName):
    """
    Get the view node for the selected 3D view
    """
    viewNode = slicer.util.getNode(viewName)
    return viewNode


  def updateNavigationView(self):
    if ( not self.navigationView == '' ): # Check first if the string is empty
      self.selectView(self.navigationView) # This automatically sets the view to ultrasound only if the string is empty. Here, we want it to do nothing.

      
  def onViewSelect(self, layoutIndex):
    Guidelet.onViewSelect(self, layoutIndex)
    
    if ( not hasattr( self, 'needleModel' ) ):
      return
      
    if ( self.needleModel is None or self.needleModel.GetDisplayNode() is None ):
      return
    
    text = self.viewSelectorComboBox.currentText
    if ( text == self.VIEW_ULTRASOUND ):
      self.needleModel.GetDisplayNode().SetSliceIntersectionVisibility(False)
    else:
      self.needleModel.GetDisplayNode().SetSliceIntersectionVisibility(True)

      
  def stopSequenceBrowserPlayback(self):
    sequenceBrowserNodes = slicer.mrmlScene.GetNodesByClass("vtkMRMLSequenceBrowserNode")
    for i in range( sequenceBrowserNodes.GetNumberOfItems() ):
      currSequenceBrowserNode = sequenceBrowserNodes.GetItemAsObject( i )
      currSequenceBrowserNode.SetPlaybackActive(False)
      self.setPlaybackRealtime(currSequenceBrowserNode)
    
      
  def onResultsPanelToggled(self, toggled):

    self.navigationView = self.parameterNode.GetParameter( "ResultsLayout" )
    self.updateNavigationView()
    logging.debug('onResultsPanelToggled')
    
    if ( self.ultrasound.startStopRecordingButton.checked ):
      self.ultrasound.startStopRecordingButton.click() # Simulate the user clicking the stop button before the panel is toggled
      # This will stop all the recording etc.
      
    # Also stop the playback        
    self.stopSequenceBrowserPlayback()

    if ( self.connectorNode is None or self.webcamConnectorNode is None ):
      return

    # If we are in the "Results" panel, stop the connection so we can replay
    if ( toggled ):
      self.connectorNode.Stop()
      self.webcamConnectorNode.Stop()
    else:
      self.connectorNode.Start()
      self.webcamConnectorNode.Start()


  def setupSliceUSMarkers(self, sliceName):
    sliceView = slicer.app.layoutManager().sliceWidget( sliceName ).sliceView()
    displayableManagers = vtk.vtkCollection()
    sliceView.getDisplayableManagers( displayableManagers )
    rulerDisplayableManager = None
    for i in range( displayableManagers.GetNumberOfItems() ):
      if ( displayableManagers.GetItemAsObject( i ).IsA( "vtkMRMLRulerDisplayableManager" ) ):
        rulerDisplayableManager = displayableManagers.GetItemAsObject( i ) #Borrow the ruler displayable manager
    if ( rulerDisplayableManager is None ):
      return
    sliceRenderer = rulerDisplayableManager.GetRenderer()

    sliceNode = sliceView.mrmlSliceNode()
    sliceLogic = slicer.app.applicationLogic().GetSliceLogic( sliceNode )
    sliceBackgroundLogic = sliceLogic.GetBackgroundLayer()

    if ( sliceRenderer is None or sliceNode is None or sliceLogic is None or sliceBackgroundLogic is None ):
      return

    usMarkersProperties = {}
    usMarkersProperties[ "Renderer" ] = sliceRenderer
    usMarkersProperties[ "Node" ] = sliceNode
    usMarkersProperties[ "Logic" ] = sliceLogic
    usMarkersProperties[ "BackgroundLogic" ] = sliceBackgroundLogic
    usMarkersProperties[ "Spheres" ] = {}
    usMarkersProperties[ "Actors" ] = {}
    usMarkersProperties[ "MarkActor" ] = None
    self.usMarkersPropertiesDict[ sliceName ] = usMarkersProperties

    usMarkersProperties[ "Node" ].AddObserver( vtk.vtkCommand.ModifiedEvent, self.displaySliceUSMarkers )
    

  def displaySliceUSMarkers(self, node, eventid):
    for sliceName, usMarkersProperties in self.usMarkersPropertiesDict.items():
      if ( usMarkersProperties[ "Node" ] is not node ):
        continue # Only update the modified slice node (otherwise we will have unnecessary updates, possibly compromising performance)

      xyToIJKTransform = usMarkersProperties[ "BackgroundLogic" ].GetXYToIJKTransform()
      ijkToXYTransform = vtk.vtkGeneralTransform()
      ijkToXYTransform.DeepCopy( xyToIJKTransform )
      ijkToXYTransform.Inverse()

      xyToRASTransform = vtk.vtkGeneralTransform()
      xyToRASTransform.Concatenate( usMarkersProperties[ "Node" ].GetXYToRAS() )

      ijkToRASTransform = vtk.vtkGeneralTransform()
      ijkToRASTransform.DeepCopy( ijkToXYTransform )
      ijkToRASTransform.PostMultiply()
      ijkToRASTransform.Concatenate( xyToRASTransform )

      # Scale between RAS and IJK
      unitVector_IJK = [ 0, 1, 0 ] # Since the dots go in the j-direction
      unitVector_RAS = [ 0, 0, 0 ]
      ijkToRASTransform.TransformVectorAtPoint( [ 0, 0, 0 ], unitVector_IJK, unitVector_RAS )
      scale = vtk.vtkMath.Norm( unitVector_RAS )

      if ( usMarkersProperties[ "BackgroundLogic" ].GetVolumeNode() is None or usMarkersProperties[ "BackgroundLogic" ].GetVolumeNode().GetImageData() is None ):
        continue
      volumeDimensions = usMarkersProperties[ "BackgroundLogic" ].GetVolumeNode().GetImageData().GetDimensions()

      DOT_SPACING = 5 #mm
      DOT_RADIUS = 6 #pixels # This is the big dot radius, the small do radius should be half of this
      DOT_COLOR = [ 0, 1, 1 ] # Same as the default IGT needle color

      dotIndex = 0
      while( dotIndex < volumeDimensions[ 1 ] * float( scale ) / DOT_SPACING ):
        # Create the sphere source and actor if necessary
        if ( dotIndex not in usMarkersProperties[ "Actors" ] or dotIndex not in usMarkersProperties[ "Spheres" ] ):
          sphereSource = vtk.vtkSphereSource()
          actor2D = vtk.vtkActor2D()
          mapper2D = vtk.vtkPolyDataMapper2D()
          mapper2D.SetInputConnection( sphereSource.GetOutputPort() )
          actor2D.SetMapper( mapper2D )
          actor2D.GetProperty().SetColor( DOT_COLOR )
          usMarkersProperties[ "Renderer" ].AddActor( actor2D )

          usMarkersProperties[ "Spheres" ][ dotIndex ] = sphereSource
          usMarkersProperties[ "Actors" ][ dotIndex ] = actor2D


        # Find the location in the XY frame
        dotPosition_IJK = [ 0, dotIndex * DOT_SPACING / scale, 0 ]
        dotPosition_XY = [ 0, 0, 0 ]
        ijkToXYTransform.TransformPoint( dotPosition_IJK, dotPosition_XY )

        usMarkersProperties[ "Spheres" ][ dotIndex ].SetCenter( dotPosition_XY )
        usMarkersProperties[ "Spheres" ][ dotIndex ].SetRadius( DOT_RADIUS - DOT_RADIUS * ( dotIndex % 2 ) / 2.0 )

        dotIndex = dotIndex + 1

      # Remove anything unncessary from the renderer and dictionaries
      sphereIndices = usMarkersProperties[ "Spheres" ].keys()
      indexesToRemove = []
      for index in sphereIndices:
        if (index >= dotIndex):
          indexesToRemove.append(index)
      for index in indexesToRemove:
        usMarkersProperties["Renderer"].RemoveActor(usMarkersProperties["Actors"][index])
        del usMarkersProperties["Actors"][index]
        del usMarkersProperties["Spheres"][index]

      # Add the text for the Marked side of the probe
      if ( usMarkersProperties[ "MarkActor" ] is None ):
        usMarkersProperties[ "MarkActor" ] = vtk.vtkTextActor()
        usMarkersProperties[ "MarkActor" ].SetInput( "M" )
        usMarkersProperties[ "MarkActor" ].GetProperty().SetColor( DOT_COLOR )
        usMarkersProperties[ "Renderer" ].AddActor( usMarkersProperties[ "MarkActor" ] )

      mSize = [ 0, 0 ]
      usMarkersProperties[ "MarkActor" ].GetSize( usMarkersProperties[ "Renderer" ], mSize )
      mPosition_IJK = [ volumeDimensions[ 0 ], 0, 0 ] # Assumes MF ultrasound orientation
      mPosition_XY = [ 0, 0, 0 ]
      ijkToXYTransform.TransformPoint( mPosition_IJK, mPosition_XY )
      usMarkersProperties[ "MarkActor" ].SetPosition( mPosition_XY[ 0 ] - mSize[ 0 ], mPosition_XY[ 1 ] - mSize[ 1 ] )

      # Rendering is already taken care of

    
  def displayImageInSliceViewer(self, imageNodeID, sliceName, flip, rotate):
    # First, find the volume reslice driver logic
    print(f"setting up display: {imageNodeID} {sliceName}")
    sliceWidget = slicer.app.layoutManager().sliceWidget( sliceName )
    '''if ( sliceWidget is None ):
      return'''

    sliceNode = sliceWidget.sliceView().mrmlSliceNode()
    sliceLogic = sliceWidget.sliceLogic()
    '''if ( sliceNode is None or sliceLogic is None ):
      return'''

    vrdLogic = slicer.modules.volumereslicedriver.logic()
    '''if ( vrdLogic is None ):
      logging.error( "LumbarTutorLogic::displayImageInSliceViewer could not find Volume Reslice Driver logic." )
      return'''

    sliceLogic.GetSliceCompositeNode().SetBackgroundVolumeID(imageNodeID)
    
    sliceNode.SetSliceResolutionMode(slicer.vtkMRMLSliceNode.SliceResolutionMatchVolumes)
    
    vrdLogic.SetDriverForSlice(imageNodeID, sliceNode)
    vrdLogic.SetModeForSlice(slicer.vtkSlicerVolumeResliceDriverLogic.MODE_TRANSVERSE, sliceNode)
    vrdLogic.SetFlipForSlice(flip, sliceNode)
    vrdLogic.SetRotationForSlice(rotate, sliceNode) # 180 degrees
    
    sliceLogic.FitSliceToAll()
  
  
  def setSequenceBrowserToolBarsVisible(self, visible, wasVisible = False):
    sequenceBrowserToolBars = slicer.util.mainWindow().findChildren( "qMRMLSequenceBrowserToolBar" )
    for toolBar in sequenceBrowserToolBars:
      toolBar.setVisible( visible )

      
  def setPlaybackRealtime(self, browserNode):
    try: # Update the playback fps rate
      sequenceNode = browserNode.GetMasterSequenceNode()   
      numDataNodes = sequenceNode.GetNumberOfDataNodes()    
      startTime = float( sequenceNode.GetNthIndexValue( 0 ) )
      stopTime = float( sequenceNode.GetNthIndexValue( numDataNodes - 1 ) )
      frameRate = numDataNodes / ( stopTime - startTime )
      browserNode.SetPlaybackRateFps( frameRate )
    except:
      logging.debug( "setPlaybackRealtime:: ", sys.exc_info()[0] )  

      
  def startSequenceBrowserRecording(self, browserNode):
    if (browserNode is None):
      return
  
    # Indicate that this node was recorded, not loaded from file
    browserNode.SetName( slicer.mrmlScene.GetUniqueNameByString( "Recording" ) )
    browserNode.SetAttribute( "Recorded", "True" )
    # Create and populate a sequence browser node if the recording started
    browserNode.SetScene(slicer.mrmlScene)    
    slicer.mrmlScene.AddNode(browserNode)
    sequenceBrowserLogic = slicer.modules.sequencebrowser.logic()
    
    modifiedFlag = browserNode.StartModify()
    sequenceBrowserLogic.AddSynchronizedNode(None, self.needleToReference, browserNode)
    sequenceBrowserLogic.AddSynchronizedNode(None, self.probeToReference, browserNode)
    sequenceBrowserLogic.AddSynchronizedNode(None, self.ultrasound_Ultrasound, browserNode)
    sequenceBrowserLogic.AddSynchronizedNode(None, self.webcam_Webcam, browserNode)
    
    # Stop overwriting and saving changes to all nodes
    browserNode.SetRecording( None, True )
    browserNode.SetOverwriteProxyName( None, False )
    browserNode.SetSaveChanges( None, False )
    browserNode.EndModify( modifiedFlag )

    browserNode.SetRecordMasterOnly(True)
    browserNode.SetRecordingActive(True)

    
  def stopSequenceBrowserRecording(self, browserNode):
    if (browserNode is None):
      return
    
    browserNode.SetRecordingActive(False)
    browserNode.SetRecording( None, False )
    self.setPlaybackRealtime(browserNode)      

    
  def onStartStopRecordingClicked(self):    
    if self.ultrasound.startStopRecordingButton.isChecked():
      self.needleTutorSequenceBrowserNode = slicer.vtkMRMLSequenceBrowserNode()
      self.startSequenceBrowserRecording(self.needleTutorSequenceBrowserNode)      
    else:
      self.stopSequenceBrowserRecording(self.needleTutorSequenceBrowserNode)
