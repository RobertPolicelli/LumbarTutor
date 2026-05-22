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
    self.parent.contributors = ["Matthew S. Holden (Perk Lab, Queen's University), Robert Policelli (Perk Lab, Queen's University), Denesh Peramakumar (Perk Lab, Queen's University)"]
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
    self.needleToReferenceObserver = None

    Guidelet.__init__(self, parent, logic, configurationName)
    logging.debug('LumbarTutorGuidelet.__init__')
    self.sequenceBrowserModule = slicer.modules.sequencebrowser if hasattr(slicer.modules, 'sequencebrowser') else None
    
    if not self.sequenceBrowserModule:
        print("Warning: SequenceBrowser module not found. Recording may be disabled.")
    
    # Setup the PLUS connectors for the webcam and depth streams. If they already exist in the scene (e.g. from a previous session), just grab them instead of creating new ones.

    try:
      self.webcam1RGBConnectorNode = slicer.util.getNode('RGB1Connector')
    except slicer.util.MRMLNodeNotFoundException:
      self.webcam1RGBConnectorNode = self.createRealSensePlusConnectors(1, 18949,'RGB')
    self.webcam1RGBConnectorNode.Start()


    try:
      self.webcam1DEPTHConnectorNode = slicer.util.getNode('DEPTH1Connector')
    except slicer.util.MRMLNodeNotFoundException:
      self.webcam1DEPTHConnectorNode = self.createRealSensePlusConnectors(1, 18950, 'DEPTH')
    self.webcam1DEPTHConnectorNode.Start()

    try:
      self.webcam0RGBConnectorNode = slicer.util.getNode('RGB0Connector')
    except slicer.util.MRMLNodeNotFoundException:
      self.webcam0RGBConnectorNode = self.createRealSensePlusConnectors(0, 18945,'RGB')
    self.webcam0RGBConnectorNode.Start()

    try:
      self.webcam0DEPTHConnectorNode = slicer.util.getNode('DEPTH0Connector')
    except slicer.util.MRMLNodeNotFoundException:
      self.webcam0DEPTHConnectorNode = self.createRealSensePlusConnectors(0, 18948, 'DEPTH')
    self.webcam0DEPTHConnectorNode.Start()

    
    moduleDirectoryPath = slicer.modules.lumbartutor.path.replace('LumbarTutor.py', '')

    # Set up main frame
    self.sliceletDockWidget.setObjectName('LumbarTutorPanel')
    self.sliceletDockWidget.setWindowTitle('Lumbar Tutor')
    self.mainWindow.setWindowTitle('Lumbar Tutor')
    self.mainWindow.windowIcon = qt.QIcon(moduleDirectoryPath + '/Resources/Icons/LumbarTutor.png')

    self.pivotCalibrationLogic = slicer.modules.pivotcalibration.logic()

    self.navigationView = self.VIEW_ULTRASOUND_3D
    self.updateNavigationView()

    self.usMarkersPropertiesDict = {}

    # Setting button open on startup.
    self.calibrationCollapsibleButton.setProperty('collapsed', True)


    moduleDir = os.path.dirname(slicer.modules.lumbartutor.path)
    sceneSaveDirectory = os.path.join(moduleDir, 'SavedScenes')
    self.logic.updateSettings({'SavedScenesDirectory': sceneSaveDirectory}, self.configurationName)
    if hasattr(self, 'parameterNode') and self.parameterNode:
      self.parameterNode.SetParameter('SavedScenesDirectory', sceneSaveDirectory)

  def createFeaturePanels(self):
    # 1. Initialize the base Guidelet panels (this safely boots up core logic)
    featurePanelList = Guidelet.createFeaturePanels(self)
    
    # 2. Hide the default tabs so they don't show up on screen
    self.ultrasoundCollapsibleButton.setVisible(False)
    self.advancedCollapsibleButton.setVisible(False) # <-- THIS COMPLETELY HIDES THE OLD SETTINGS TAB

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
    
    return featurePanelList

  def createRealSensePlusConnectors(self,cameraNumber,port,imageType):
    connectorNodeName = imageType + str(cameraNumber) + "Connector"
    try:
      realsenseConnectorNode = slicer.util.getNode(connectorNodeName)
    except slicer.util.MRMLNodeNotFoundException:
      # if not webcamConnectorNode:
      realsenseConnectorNode = slicer.vtkMRMLIGTLConnectorNode()
      realsenseConnectorNode.SetName(connectorNodeName)
      slicer.mrmlScene.AddNode(realsenseConnectorNode)
      hostName = "localhost"
      realsenseConnectorNode.SetTypeClient(hostName,int(port))
      logging.debug(connectorNodeName + ' Created')
    return realsenseConnectorNode

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
    self.l1Button.connect('clicked(bool)', self.onL1Clicked)
    self.l2Button.connect('clicked(bool)', self.onL2Clicked)
    self.l3Button.connect('clicked(bool)', self.onL3Clicked)
    self.l4Button.connect('clicked(bool)', self.onL4Clicked)
    self.l5Button.connect('clicked(bool)', self.onL5Clicked)
    self.togglePostureButton.connect('clicked(bool)', self.onTogglePostureClicked)
    self.anatomyCompleteButton.connect('clicked(bool)', self.onAnatomyCompleteClicked)
    self.calibrationCollapsibleButton.connect('toggled(bool)', self.onCalibrationSetupPanelToggled)
    self.procedureCollapsibleButton.connect('toggled(bool)', self.onProcedureTabToggled)
    self.anatomyCollapsibleButton.connect('toggled(bool)', self.onAnatomyTabToggled)
    
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
      self.needleToReference = slicer.util.getNode('NeedleToReference')
    except slicer.util.MRMLNodeNotFoundException:
      self.needleToReference = slicer.vtkMRMLLinearTransformNode()
      self.needleToReference.SetName('NeedleToReference')
      slicer.mrmlScene.AddNode(self.needleToReference)

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

    self.webcam_Webcam = None
    
    # Load the spine "scenes"
    logging.debug('Create spine scenes')
    
    '''spineScenes = glob.glob( os.path.join( moduleDir, 'Resources', 'SpineScenes', "*.mrb" ) )
    for spine in spineScenes:
      slicer.util.loadScene( spine )'''

    # Build transform tree
    logging.debug('Set up transform tree')

    self.needleToReference.SetAndObserveTransformNodeID(self.referenceToRas.GetID())
    self.needleTipToNeedle.SetAndObserveTransformNodeID(self.needleToReference.GetID())
    self.needleModel.SetAndObserveTransformNodeID(self.needleTipToNeedle.GetID())
    self.startNeedleTrackingDisplay()
    

    # Ensure that the sequence browser toolbar(s) is not made visible
    sequenceBrowserToolBars = slicer.util.mainWindow().findChildren( "qMRMLSequenceBrowserToolBar" )
    for toolBar in sequenceBrowserToolBars:
      toolBar.connect('visibilityChanged(bool)', partial( self.setSequenceBrowserToolBarsVisible, False ) )

    # Hide the empty 2D planes floating inside the 3D viewer
    slicer.util.getNode('vtkMRMLSliceNodeRed').SetSliceVisible(False)
    slicer.util.getNode('vtkMRMLSliceNodeYellow').SetSliceVisible(False)
    slicer.util.getNode('vtkMRMLSliceNodeGreen').SetSliceVisible(False)

    # ==========================================
    # INTERACTIVE ANATOMY MODELS
    # ==========================================
    # 1. Load the neutral models
    self.anatomyModels = {
        "L1": self.loadOrCreateModel('L1Model', '1308055L1EXT.stl', (0.9, 0.9, 0.7)),
        "L2": self.loadOrCreateModel('L2Model', '1308055L2EXT.stl', (0.9, 0.9, 0.7)),
        "L3": self.loadOrCreateModel('L3Model', '1308055L3EXT.stl', (0.9, 0.9, 0.7)),
        "L4": self.loadOrCreateModel('L4Model', '1308055L4EXT.stl', (0.9, 0.9, 0.7)),
        "L5": self.loadOrCreateModel('L5Model', '1308055L5EXT.stl', (0.9, 0.9, 0.7))
    }
    
    self.extendedAnatomyModels = {
        "L1": self.loadOrCreateModel('L1Model_Ext', '1308055L1FLEX.stl', (0.9, 0.9, 0.7)),
        "L2": self.loadOrCreateModel('L2Model_Ext', '1308055L2FLEX.stl', (0.9, 0.9, 0.7)),
        "L3": self.loadOrCreateModel('L3Model_Ext', '1308055L3FLEX.stl', (0.9, 0.9, 0.7)),
        "L4": self.loadOrCreateModel('L4Model_Ext', '1308055L4FLEX.stl', (0.9, 0.9, 0.7)),
        "L5": self.loadOrCreateModel('L5Model_Ext', '1308055L5FLEX.stl', (0.9, 0.9, 0.7))
    }
    
    self.nonAnatomyTabModel = self.loadOrCreateModel(
        'NonAnatomyTabModel',
        'LumbarShellandSpine1.stl',
        (0.2, 0.8, 1.0)
    )

    if self.nonAnatomyTabModel and self.nonAnatomyTabModel.GetDisplayNode():
        self.nonAnatomyTabModel.GetDisplayNode().SetVisibility(False)
        
    self.spinalCanalModel = self.loadOrCreateModel('SpinalCanalModel', 'curved_spinal_canal.stl', (1.0, 0.85, 0.2)) # Yellow color
    if self.spinalCanalModel and self.spinalCanalModel.GetDisplayNode():
        self.spinalCanalModel.GetDisplayNode().SetVisibility(False)
        # Ensure it moves with the rest of the spine when tilted
        if hasattr(self, 'spineTiltTransform'):
            self.spinalCanalModel.SetAndObserveTransformNodeID(self.spineTiltTransform.GetID())

    self.spinalCanalModel_Ext = self.loadOrCreateModel('SpinalCanalModel_Ext', 'curved_spinal_canal_Flex.stl', (1.0, 0.85, 0.2))
    if self.spinalCanalModel_Ext and self.spinalCanalModel_Ext.GetDisplayNode():
        self.spinalCanalModel_Ext.GetDisplayNode().SetVisibility(False)

    # Hide the extended models initially so they don't overlap the neutral ones
    for modelNode in self.extendedAnatomyModels.values():
      if modelNode and modelNode.GetDisplayNode():
        modelNode.GetDisplayNode().SetVisibility(False)
        
    self.isExtendedPosture = False # Track which state we are currently in

    self.alignExtendedModelsToNeutral()

    # ==========================================
    # 3D SCREEN TEXT OVERLAY
    # ==========================================
    layoutManager = slicer.app.layoutManager()
    threeDWidget = layoutManager.threeDWidget(0)
    
    if threeDWidget:
      # Grab the actual camera renderer for the 3D view
      self.renderer = threeDWidget.threeDView().renderWindow().GetRenderers().GetFirstRenderer()
      
      # Create the text
      self.postureTextActor = vtk.vtkTextActor()
      self.postureTextActor.SetInput("Posture: NEUTRAL")
      
      # 1. Make the text much bigger (was 28, now 48)
      self.postureTextActor.GetTextProperty().SetFontSize(48) 
      self.postureTextActor.GetTextProperty().SetColor(0.2, 0.8, 1.0) # Light blue
      self.postureTextActor.GetTextProperty().BoldOn()
      
      # 2. Tell the text to anchor itself from its absolute center
      self.postureTextActor.GetTextProperty().SetJustificationToCentered()
      self.postureTextActor.GetTextProperty().SetVerticalJustificationToTop()
      
      # 3. Use "Normalized" coordinates so it stays centered even if the window resizes
      self.postureTextActor.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
      
      # Set X to 0.5 (dead center horizontally) and Y to 0.05 (very bottom of the screen)
      self.postureTextActor.SetPosition(0.5, 0.05) 
      
      self.postureTextActor.SetVisibility(False) # Keep hidden until Anatomy tab opens
      
      # Add it to the screen
      self.renderer.AddActor(self.postureTextActor)

    # 2. Create the "Click Catcher" Markups Node
    try:
      self.clickCatcherNode = slicer.util.getNode('AnatomyClickCatcher')
    except slicer.util.MRMLNodeNotFoundException:
      self.clickCatcherNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "AnatomyClickCatcher")
      self.clickCatcherNode.GetDisplayNode().SetTextScale(0) 
      
    self.clickCatcherObserver = self.clickCatcherNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointPositionDefinedEvent, self.onAnatomy3DClicked)
    interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
    self.interactionObserver = interactionNode.AddObserver(slicer.vtkMRMLInteractionNode.InteractionModeChangedEvent, self.enforceCrosshairs)
    # Wait half a second for the 3D viewer to finish loading, then trigger the tab logic
    qt.QTimer.singleShot(500, lambda: self.onAnatomyTabToggled(True))

    self.userID = "UnknownUser" 
    self.createLoginPage()
    # Temporarily hide the main procedure panel and show the login panel instead
    self.sliceletDockWidget.setWidget(self.loginPanel)

    # Camera Setup
    try:
      self.webcam1RGB = slicer.util.getNode('Image1RGB_Image1RGB')
    except slicer.util.MRMLNodeNotFoundException:
      # if not self.webcamReference:
      imageSpacing = [0.2, 0.2, 0.2]
      imageData = vtk.vtkImageData()
      imageData.SetDimensions(640, 480, 1)
      imageData.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)
      thresholder = vtk.vtkImageThreshold()
      thresholder.SetInputData(imageData)
      thresholder.SetInValue(0)
      thresholder.SetOutValue(0)
      # Create volume node
      #self.webcam1RGB = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLStreamingVolumeNode")
      self.webcam1RGB = slicer.vtkMRMLStreamingVolumeNode()
      self.webcam1RGB.SetDefaultSequenceStorageNodeClassName("vtkMRMLStreamingVolumeSequenceStorageNode")
      self.webcam1RGB.SetName('Image1RGB_Image1RGB')
      self.webcam1RGB.SetSpacing(imageSpacing)
      self.webcam1RGB.SetImageDataConnection(thresholder.GetOutputPort())
      # Add volume to scene
      slicer.mrmlScene.AddNode(self.webcam1RGB)
      displayNode = slicer.vtkMRMLVectorVolumeDisplayNode()
      slicer.mrmlScene.AddNode(displayNode)
      self.webcam1RGB.SetAndObserveDisplayNodeID(displayNode.GetID())
    self.ensureVolumeDisplayNode(self.webcam1RGB, True)

    try:
      self.webcam1DEPTH = slicer.util.getNode('Image1DEPTH_Image1DE')

    except slicer.util.MRMLNodeNotFoundException:
      # if not self.webcamReference:
      imageSpacing = [0.2, 0.2, 0.2]
      imageData = vtk.vtkImageData()
      imageData.SetDimensions(640, 480, 1)
      imageData.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)
      thresholder = vtk.vtkImageThreshold()
      thresholder.SetInputData(imageData)
      thresholder.SetInValue(0)
      thresholder.SetOutValue(0)
      # Create volume node
      #self.webcam1DEPTH = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLStreamingVolumeNode")
      self.webcam1DEPTH = slicer.vtkMRMLStreamingVolumeNode()
      self.webcam1DEPTH.SetDefaultSequenceStorageNodeClassName("vtkMRMLStreamingVolumeSequenceStorageNode")
      self.webcam1DEPTH.SetName('Image1DEPTH_Image1DE')
      self.webcam1DEPTH.SetSpacing(imageSpacing)
      self.webcam1DEPTH.SetImageDataConnection(thresholder.GetOutputPort())
      # Add volume to scene
      slicer.mrmlScene.AddNode(self.webcam1DEPTH)
      displayNode = slicer.vtkMRMLVectorVolumeDisplayNode()
      slicer.mrmlScene.AddNode(displayNode)
      self.webcam1DEPTH.SetAndObserveDisplayNodeID(displayNode.GetID())
    self.ensureVolumeDisplayNode(self.webcam1DEPTH, True)

    try:
      self.webcam0RGB = slicer.util.getNode('ImageRGB_ImageRGB')

    except slicer.util.MRMLNodeNotFoundException:
      # if not self.webcamReference:
      imageSpacing = [0.2, 0.2, 0.2]
      imageData = vtk.vtkImageData()
      imageData.SetDimensions(640, 480, 1)
      imageData.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)
      thresholder = vtk.vtkImageThreshold()
      thresholder.SetInputData(imageData)
      thresholder.SetInValue(0)
      thresholder.SetOutValue(0)
      # Create volume node
      #self.webcam0RGB = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLStreamingVolumeNode")
      self.webcam0RGB = slicer.vtkMRMLStreamingVolumeNode()
      self.webcam0RGB.SetDefaultSequenceStorageNodeClassName("vtkMRMLStreamingVolumeSequenceStorageNode")
      self.webcam0RGB.SetName('ImageRGB_ImageRGB')
      self.webcam0RGB.SetSpacing(imageSpacing)
      self.webcam0RGB.SetImageDataConnection(thresholder.GetOutputPort())
      # Add volume to scene
      slicer.mrmlScene.AddNode(self.webcam0RGB)
      displayNode = slicer.vtkMRMLVectorVolumeDisplayNode()
      slicer.mrmlScene.AddNode(displayNode)
      self.webcam0RGB.SetAndObserveDisplayNodeID(displayNode.GetID())
    self.ensureVolumeDisplayNode(self.webcam0RGB, True)

    try:
      self.webcam0DEPTH = slicer.util.getNode('ImageDEPTH_ImageDEPT')

    except slicer.util.MRMLNodeNotFoundException:
      # if not self.webcamReference:
      imageSpacing = [0.2, 0.2, 0.2]
      imageData = vtk.vtkImageData()
      imageData.SetDimensions(640, 480, 1)
      imageData.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)
      thresholder = vtk.vtkImageThreshold()
      thresholder.SetInputData(imageData)
      thresholder.SetInValue(0)
      thresholder.SetOutValue(0)
      # Create volume node
      #self.webcam0DEPTH = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLStreamingVolumeNode")
      self.webcam0DEPTH = slicer.vtkMRMLStreamingVolumeNode()
      self.webcam0DEPTH.SetDefaultSequenceStorageNodeClassName("vtkMRMLStreamingVolumeSequenceStorageNode")
      self.webcam0DEPTH.SetName('ImageDEPTH_ImageDEPT')
      self.webcam0DEPTH.SetSpacing(imageSpacing)
      self.webcam0DEPTH.SetImageDataConnection(thresholder.GetOutputPort())
      # Add volume to scene
      slicer.mrmlScene.AddNode(self.webcam0DEPTH)
      displayNode = slicer.vtkMRMLVectorVolumeDisplayNode()
      slicer.mrmlScene.AddNode(displayNode)
      self.webcam0DEPTH.SetAndObserveDisplayNodeID(displayNode.GetID())
    self.ensureVolumeDisplayNode(self.webcam0DEPTH, True)
    self.setupWebcamResliceDriver()
    self.webcam_Webcam = self.webcam1RGB
    qt.QTimer.singleShot(1000, self.printDepthImageDebugInfo)
    qt.QTimer.singleShot(1000, self.refitWebcamSliceView)
    qt.QTimer.singleShot(3000, self.refitWebcamSliceView)

    # Set up 3D camera

    layoutManager = slicer.app.layoutManager()
    viewCount = layoutManager.threeDViewCount
    if viewCount < 1:
      logging.error('No 3D views found!')
      return

    self.first3dView = layoutManager.threeDWidget(0).threeDView()
    self.firstViewNode = self.first3dView.mrmlViewNode()
    renderer = self.first3dView.renderWindow().GetRenderers().GetItemAsObject(0)

    camerasLogic = slicer.modules.cameras.logic()
    self.sceneCamera = camerasLogic.GetViewActiveCameraNode(self.firstViewNode)
    camera = self.sceneCamera.GetCamera()

    camera.SetPosition(0.0, 800, 1400.0)  # 120 cm behind and 10 cm below neck
    camera.SetFocalPoint(0.0, 0.0, 0.0)
    camera.SetViewUp(0.0, 0.0, 1.0)  # Head up, looking towards A
    camera.SetRoll(0)  # Default in Slicer

    renderer.ResetCameraClippingRange()


  
  def createLoginPage(self):
    self.loginPanel = qt.QFrame()
    self.loginPanelLayout = qt.QVBoxLayout(self.loginPanel)

    self.loginButtonLayout = qt.QFormLayout()

    self.spacer = qt.QLabel('\n\n\n\n\n\n')
    self.loginButtonLayout.addWidget(self.spacer)
    
    self.userIDLineEdit = qt.QLineEdit('User ID')
    self.loginButtonLayout.addWidget(self.userIDLineEdit)

    self.loginPushButton = qt.QPushButton('Login')
    self.loginButtonLayout.addWidget(self.loginPushButton)
    self.loginPushButton.connect('clicked()', self.onLoginClicked)

    self.loginPanelLayout.addLayout(self.loginButtonLayout)

  def onLoginClicked(self):
    if self.userIDLineEdit.text != '' and self.userIDLineEdit.text != 'User ID':
      self.userID = self.userIDLineEdit.text
      self.sliceletDockWidget.setWindowTitle('Lumbar Tutor - User: ' + self.userID)
    else:
      self.userID = "UnknownUser"
      self.sliceletDockWidget.setWindowTitle('Lumbar Tutor - UnknownUser')

    # Swap the dock widget content back to the main procedure UI
    self.sliceletDockWidget.setWidget(self.sliceletPanel)
    
  def onLogoutButtonClicked(self):
    self.sliceletDockWidget.setWindowTitle('Lumbar Tutor')
    self.sliceletDockWidget.setWidget(self.loginPanel)
    self.userIDLineEdit.setText('User ID')
    self.userID = "UnknownUser"

  def loadOrCreateModel(self, nodeName, fileName, color):
    """Helper to load a model from Resources, or create a blank one if the file is missing."""
    try:
      return slicer.util.getNode(nodeName)
    except slicer.util.MRMLNodeNotFoundException:
      moduleDir = os.path.dirname(slicer.modules.lumbartutor.path)
      filePath = os.path.join(moduleDir, 'Resources', fileName)
      
      print(f"Attempting to load {nodeName} from: {filePath}")
      
      if os.path.exists(filePath):
        model = slicer.util.loadModel(filePath)
        model.SetName(nodeName)
        
        # ==========================================
        # AUTO-ROTATION LOGIC
        # ==========================================
        # 1. Create a mathematical transform to spin the model
        transform = vtk.vtkTransform()
        
        # Rotate 180 degrees around the Superior/Inferior (Z) axis.
        # (If "horizontal" means something else for your specific files, 
        # you can change this to transform.RotateX(180) or transform.RotateY(180)!)
        transform.RotateZ(180) 
        
        # 2. Apply the spin directly to the raw 3D mesh data
        transformFilter = vtk.vtkTransformPolyDataFilter()
        transformFilter.SetInputData(model.GetPolyData())
        transformFilter.SetTransform(transform)
        transformFilter.Update()
        
        # 3. Save the permanently flipped mesh back into the model
        model.SetAndObservePolyData(transformFilter.GetOutput())
        # ==========================================

        print(f"SUCCESS: Loaded and rotated {fileName} into the scene!")
      else:
        print(f"ERROR: Could not find file at {filePath}. Creating empty invisible model.")
        model = slicer.vtkMRMLModelNode()
        model.SetName(nodeName)
        slicer.mrmlScene.AddNode(model)
        model.SetAndObservePolyData(vtk.vtkPolyData())
      
      model.CreateDefaultDisplayNodes()
      model.GetDisplayNode().SetColor(color)
      return model

  def ensureVolumeDisplayNode(self, volumeNode, isVector):
    if not volumeNode:
      return

    displayNode = volumeNode.GetDisplayNode()
    expectedClassName = 'vtkMRMLVectorVolumeDisplayNode' if isVector else 'vtkMRMLScalarVolumeDisplayNode'
    if displayNode and displayNode.IsA(expectedClassName):
      return

    if isVector:
      displayNode = slicer.vtkMRMLVectorVolumeDisplayNode()
    else:
      displayNode = slicer.vtkMRMLScalarVolumeDisplayNode()
    slicer.mrmlScene.AddNode(displayNode)
    volumeNode.SetAndObserveDisplayNodeID(displayNode.GetID())

  def ensureVolumeImageComponents(self, volumeNode, componentCount):
    if not volumeNode:
      return

    imageData = volumeNode.GetImageData()
    if imageData and imageData.GetNumberOfScalarComponents() == componentCount:
      return

    imageData = vtk.vtkImageData()
    imageData.SetDimensions(640, 480, 1)
    imageData.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, componentCount)
    imageData.GetPointData().GetScalars().Fill(0)
    volumeNode.SetAndObserveImageData(imageData)

  def applyDepthColorMap(self, volumeNode):
    displayNode = volumeNode.GetDisplayNode() if volumeNode else None
    if not displayNode:
      return

    colorNode = None
    for colorNodeName in ['ColdToHotRainbow', 'Rainbow', 'vtkMRMLColorTableNodeFileColdToHotRainbow.txt']:
      try:
        colorNode = slicer.util.getNode(colorNodeName)
        break
      except slicer.util.MRMLNodeNotFoundException:
        pass

    if colorNode:
      displayNode.SetAndObserveColorNodeID(colorNode.GetID())
    if hasattr(displayNode, 'SetAutoWindowLevel'):
      displayNode.SetAutoWindowLevel(True)

  def printDepthImageDebugInfo(self):
    try:
      n = slicer.util.getNode('Image1DEPTH_Image1DE')
      img = n.GetImageData()
      if not img:
        print('Image1DEPTH_Image1DE has no image data yet.')
        return
      print(img.GetDimensions())
      print(img.GetScalarTypeAsString())
      print(img.GetNumberOfScalarComponents())
      displayNode = n.GetDisplayNode()
      print(displayNode.GetClassName() if displayNode else 'No display node')
    except Exception as e:
      print('Could not print Image1DEPTH debug info: ' + str(e))

  def setupWebcamResliceDriver(self):
    """Show the primary RGB webcam stream in the Yellow slice view."""
    if not hasattr(self, 'webcam1RGB') or self.webcam1RGB is None:
      try:
        self.webcam1RGB = slicer.util.getNode('Image1RGB_Image1RGB')
      except slicer.util.MRMLNodeNotFoundException:
        logging.warning('Webcam RGB node not found; skipping webcam reslice driver setup.')
        return

    layoutManager = slicer.app.layoutManager()
    yellowSlice = layoutManager.sliceWidget('Yellow')
    if yellowSlice is None:
      logging.warning('Yellow slice view not found; skipping webcam reslice driver setup.')
      return

    yellowSliceLogic = yellowSlice.sliceLogic()
    yellowNode = yellowSlice.sliceView().mrmlSliceNode()
    yellowSliceLogic.GetSliceCompositeNode().SetBackgroundVolumeID(self.webcam1RGB.GetID())
    yellowNode.SetSliceResolutionMode(slicer.vtkMRMLSliceNode.SliceResolutionMatchVolumes)

    resliceLogic = slicer.modules.volumereslicedriver.logic()
    if resliceLogic:
      resliceLogic.SetDriverForSlice(self.webcam1RGB.GetID(), yellowNode)
      resliceLogic.SetModeForSlice(slicer.vtkSlicerVolumeResliceDriverLogic.MODE_TRANSVERSE, yellowNode)
      resliceLogic.SetFlipForSlice(False, yellowNode)

    yellowSliceLogic.FitSliceToAll()

  def refitWebcamSliceView(self):
    layoutManager = slicer.app.layoutManager()
    yellowSlice = layoutManager.sliceWidget('Yellow')
    if not yellowSlice:
      return

    yellowSliceLogic = yellowSlice.sliceLogic()
    yellowSliceLogic.FitSliceToAll()

    
  def disconnect(self):#TODO see connect
    logging.debug('LumbarTutor.disconnect()')
    Guidelet.disconnect(self)
    # Inside disconnect(self):    
    self.l1Button.disconnect('clicked(bool)', self.onL1Clicked)
    self.l2Button.disconnect('clicked(bool)', self.onL2Clicked)
    self.l3Button.disconnect('clicked(bool)', self.onL3Clicked)
    self.l4Button.disconnect('clicked(bool)', self.onL4Clicked)
    self.l5Button.disconnect('clicked(bool)', self.onL5Clicked)
    self.togglePostureButton.disconnect('clicked(bool)', self.onTogglePostureClicked)
    self.anatomyCompleteButton.disconnect('clicked(bool)', self.onAnatomyCompleteClicked)
    self.compStep1Button.disconnect('clicked(bool)', self.onCompStep1Clicked)
    self.compStep2Button.disconnect('clicked(bool)', self.onCompStep2Clicked)
    self.compStep3Button.disconnect('clicked(bool)', self.onCompStep3Clicked)

    self.calibrationCollapsibleButton.disconnect('toggled(bool)', self.onCalibrationSetupPanelToggled)
    self.procedureCollapsibleButton.disconnect('toggled(bool)', self.onProcedureTabToggled)
    self.anatomyCollapsibleButton.disconnect('toggled(bool)', self.onAnatomyTabToggled)
    
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
      self.clickCatcherNode.RemoveObserver(self.clickCatcherObserver)
    except AttributeError:
      pass
    try:
      interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
      if interactionNode and hasattr(self, 'interactionObserver'):
        interactionNode.RemoveObserver(self.interactionObserver)
    except AttributeError:
      pass

    self.stopNeedleTrackingDisplay()

    try:
      self.loadButton.disconnect('clicked()', self.onLoadButtonClicked)
      self.saveButton.disconnect('clicked()', self.saveAllRecordings)
      self.exitButton.disconnect('clicked()', self.onExitButtonClicked)
    except AttributeError:
      pass

    try:
      self.topRecordButton.disconnect('clicked()', self.onTopRecordButtonClicked)
      self.logoutButton.disconnect('clicked()', self.onLogoutButtonClicked)
      self.loginPushButton.disconnect('clicked()', self.onLoginClicked)
    except AttributeError:
      pass

    try:
      self.topRecordButton.disconnect('clicked()', self.onTopRecordButtonClicked)
      self.logoutButton.disconnect('clicked()', self.onLogoutButtonClicked)
      self.loginPushButton.disconnect('clicked()', self.onLoginClicked)
      self.settingsButton.disconnect('clicked()', self.onOpenSettingsClicked)
      
      # Settings Window Disconnects
      self.showFullSlicerInterfaceButton.disconnect('clicked()', self.onShowFullSlicerInterfaceClicked)
      self.showGuideletFullscreenButton.disconnect('clicked()', self.onShowGuideletFullscreenButton)
      self.saveSceneButton.disconnect('clicked()', self.onSaveSceneClicked)
      self.saveDirectoryLineEdit.disconnect('currentPathChanged(QString)', self.onSaveDirectoryPreferencesChanged)
      self.closeSettingsButton.disconnect('clicked()', self.settingsWidget.hide)
    except AttributeError:
      pass

    try:
      self.procedureStartRecordingButton.disconnect('clicked()', self.onProcedureStartRecordingClicked)
      self.procedureStopRecordingButton.disconnect('clicked()', self.onProcedureStopRecordingClicked)
    except AttributeError:
      pass
    
    # Keyboard shortcuts
    self.startStopShortcutPlus.disconnect('activated()', self.ultrasound.startStopRecordingButton.click )
    try:
      self.advanceStepShortcut.disconnect('activated()', self.onAdvanceStepShortcut)
    except AttributeError:
      pass


  def onAnatomyTabToggled(self, toggled):
    """Triggers when the Anatomy tab opens or closes."""
    if toggled:
      if hasattr(self, 'nonAnatomyTabModel') and self.nonAnatomyTabModel.GetDisplayNode():
        self.nonAnatomyTabModel.GetDisplayNode().SetVisibility(False)

      if hasattr(self, 'postureTextActor'):
        self.postureTextActor.SetVisibility(True)
        slicer.app.layoutManager().threeDWidget(0).threeDView().scheduleRender()
      self.tiltSpineModels(0)
      self.calibrationCollapsibleButton.setProperty('collapsed', True)
      self.procedureCollapsibleButton.setProperty('collapsed', True)
      
      # --- Ensure the correct models are visible when the tab opens ---
      is_ext = getattr(self, 'isExtendedPosture', False)
      for key in self.anatomyModels:
        neu = self.anatomyModels.get(key)
        ext = self.extendedAnatomyModels.get(key)
        if neu and neu.GetDisplayNode(): 
          neu.GetDisplayNode().SetVisibility(not is_ext)
        if ext and ext.GetDisplayNode(): 
          ext.GetDisplayNode().SetVisibility(is_ext)

      if getattr(self, 'currentAnatomyTarget', "") == "Done":
        if getattr(self, 'isExtendedPosture', False):
            if hasattr(self, 'spinalCanalModel_Ext') and self.spinalCanalModel_Ext.GetDisplayNode():
                self.spinalCanalModel_Ext.GetDisplayNode().SetVisibility(True)
        else:
            if hasattr(self, 'spinalCanalModel') and self.spinalCanalModel.GetDisplayNode():
                self.spinalCanalModel.GetDisplayNode().SetVisibility(True)
          
      if not getattr(self, 'anatomyReviewCompleted', False):
        
        # Only set to L1 if they haven't started yet (prevents resetting their progress)
        if not hasattr(self, 'currentAnatomyTarget'):
          self.currentAnatomyTarget = "L1" 
          
        # Turn on the crosshairs since they are still working on it
        qt.QTimer.singleShot(100, self.activateCrosshairs)
        
      else:
        # If they are done and just reopening the tab, leave the mouse in scroll/rotate mode!
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
          interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.ViewTransform)
          
    else: # Tab is closing

      if hasattr(self, 'nonAnatomyTabModel') and self.nonAnatomyTabModel.GetDisplayNode():
        self.nonAnatomyTabModel.GetDisplayNode().SetVisibility(True)

      # Turn off the crosshairs if the user closes the Anatomy tab
      interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
      if interactionNode:
        interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.ViewTransform)
        
      for modelNode in self.anatomyModels.values():
        if modelNode and modelNode.GetDisplayNode():
          modelNode.GetDisplayNode().SetVisibility(False)
          
      for modelNode in getattr(self, 'extendedAnatomyModels', {}).values():
        if modelNode and modelNode.GetDisplayNode():
          modelNode.GetDisplayNode().SetVisibility(False)

      if hasattr(self, 'spinalCanalModel') and self.spinalCanalModel.GetDisplayNode():
          self.spinalCanalModel.GetDisplayNode().SetVisibility(False)
      if hasattr(self, 'spinalCanalModel_Ext') and self.spinalCanalModel_Ext.GetDisplayNode():
          self.spinalCanalModel_Ext.GetDisplayNode().SetVisibility(False)
          
      if hasattr(self, 'postureTextActor'):
        self.postureTextActor.SetVisibility(False)
        slicer.app.layoutManager().threeDWidget(0).threeDView().scheduleRender()

  def activateCrosshairs(self):
    """Safely forces the Slicer mouse into Fiducial Placement mode."""
    selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
    interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
    
    if selectionNode and interactionNode and self.clickCatcherNode:
      # Tell Slicer we want to place points
      selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
      
      # Tell Slicer to put those points into our specific Catcher node
      # (This is the SAFE command that officially takes the .GetID() string without crashing)
      selectionNode.SetActivePlaceNodeID(self.clickCatcherNode.GetID())
      
      # Force the mouse into persistent Place mode
      interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.Place)
      interactionNode.SetPlaceModePersistence(1)

  def enforceCrosshairs(self, caller, event):
    """Instantly restores crosshairs if Slicer tries to drop them during the active review."""
    # 1. If we aren't in the Anatomy tab, let Slicer act normally
    if self.anatomyCollapsibleButton.collapsed:
      return
      
    # 2. If the user has already finished L5, let them drop the tool to look around
    if getattr(self, 'anatomyReviewCompleted', False) or getattr(self, 'currentAnatomyTarget', "") == "Done":
      return
      
    # 3. If Slicer changed the mode to anything other than Place, FORCE it back!
    if caller.GetCurrentInteractionMode() != slicer.vtkMRMLInteractionNode.Place:
      qt.QTimer.singleShot(0, self.activateCrosshairs)
  
  def onAnatomy3DClicked(self, caller, event):
    """Triggers whenever the user clicks the 3D viewer in the Anatomy tab."""
    lastIndex = self.clickCatcherNode.GetNumberOfControlPoints() - 1
    if lastIndex < 0: return
    
    clickPosition_RAS = [0, 0, 0]
    self.clickCatcherNode.GetNthControlPointPosition(lastIndex, clickPosition_RAS)
    
    qt.QTimer.singleShot(10, self.clickCatcherNode.RemoveAllControlPoints)

    targetModel = self.anatomyModels.get(self.currentAnatomyTarget)

    # Increased tolerance slightly to account for Slicer's surface-snapping math
    if self.isClickOnModel(clickPosition_RAS, targetModel, tolerance_mm=15.0):
      print(f"Correct! User successfully identified {self.currentAnatomyTarget}.")
      slicer.util.showStatusMessage(f"Correct: {self.currentAnatomyTarget} identified!", 3000)
      
      # --- FIXED: Route 3D clicks directly to your button functions! ---
      # This ensures the STL click shares the exact same "brain" as the UI buttons.
      if self.currentAnatomyTarget == "L1":
        self.onL1Clicked()
      elif self.currentAnatomyTarget == "L2":
        self.onL2Clicked()
      elif self.currentAnatomyTarget == "L3":
        self.onL3Clicked()
      elif self.currentAnatomyTarget == "L4":
        self.onL4Clicked()
      elif self.currentAnatomyTarget == "L5":
        self.onL5Clicked()
        
    else:
      slicer.util.showStatusMessage(f"Incorrect. Please click the {self.currentAnatomyTarget}.", 3000)

    # Check if we hit L5 before deciding whether to turn crosshairs back on
    if getattr(self, 'currentAnatomyTarget', "") != "Done" and not getattr(self, 'anatomyReviewCompleted', False):
      qt.QTimer.singleShot(50, self.activateCrosshairs)

  def tiltSpineModels(self, angle_degrees):
    """Tilts the entire spine by rotating around the X-axis (Right/Left)."""
    try:
      self.spineTiltTransform = slicer.util.getNode('SpineTiltTransform')
    except slicer.util.MRMLNodeNotFoundException:
      self.spineTiltTransform = slicer.vtkMRMLLinearTransformNode()
      self.spineTiltTransform.SetName('SpineTiltTransform')
      slicer.mrmlScene.AddNode(self.spineTiltTransform)

    # 1. Create a mathematical transform for the rotation
    transform = vtk.vtkTransform()
    
    # In Slicer's RAS coordinate system, the X-axis is Right-to-Left. 
    # Rotating around X tilts models anteriorly/posteriorly (forward/backward).
    # (Note: If your specific STLs tilt forward instead of backward, just change this to -angle_degrees)
    transform.RotateX(angle_degrees) 
    
    # 2. Apply it to our Slicer Transform Node
    self.spineTiltTransform.SetMatrixTransformToParent(transform.GetMatrix())

    # 3. Attach all neutral models to this new transform
    for model in getattr(self, 'anatomyModels', {}).values():
      if model:
        model.SetAndObserveTransformNodeID(self.spineTiltTransform.GetID())

    # 4. Attach the Extended models' base transform to this new transform.
    # This preserves your exact distance alignment while tilting the whole group!
    if hasattr(self, 'extendedAlignmentTransform') and self.extendedAlignmentTransform:
      self.extendedAlignmentTransform.SetAndObserveTransformNodeID(self.spineTiltTransform.GetID())

    if hasattr(self, 'spinalCanalModel') and self.spinalCanalModel:
      self.spinalCanalModel.SetAndObserveTransformNodeID(self.spineTiltTransform.GetID())
  
  def setNonAnatomyTabModelVisible(self, visible):
    if hasattr(self, 'nonAnatomyTabModel') and self.nonAnatomyTabModel:
        displayNode = self.nonAnatomyTabModel.GetDisplayNode()
        if displayNode:
            displayNode.SetVisibility(visible)
            
  def isClickOnModel(self, clickPosition_RAS, modelNode, tolerance_mm=10.0): # <--- Increased to 10.0
    """Uses VTK math to check if a 3D coordinate is physically touching a specific model."""
    if not modelNode or not modelNode.GetPolyData() or modelNode.GetPolyData().GetNumberOfPoints() == 0:
      print("Warning: Target model is empty or not loaded.")
      return False
      
    locator = vtk.vtkCellLocator()
    locator.SetDataSet(modelNode.GetPolyData())
    locator.BuildLocator()
    
    closestPoint = [0.0, 0.0, 0.0]
    cellId = vtk.reference(0)
    subId = vtk.reference(0)
    dist2 = vtk.reference(0.0)
    
    locator.FindClosestPoint(clickPosition_RAS, closestPoint, cellId, subId, dist2)
    
    import math
    distance_mm = math.sqrt(dist2.get())
    
    print(f"Distance to target: {distance_mm:.2f} mm") 
    
    return distance_mm <= tolerance_mm
  
  def onAdvanceStepShortcut(self):
    """Triggered when the user presses 'p'. Only advances Procedure steps."""
    
    # --- Check if Procedure Tab is open ---
    if not self.procedureCollapsibleButton.collapsed:
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
    else:
      # If they press 'p' in Anatomy, do nothing or show a message
      slicer.util.showStatusMessage("Please identify the anatomy by clicking the 3D model.", 2000)
    
  # ==========================================
  # ANATOMY CLICK LOGIC
  # ==========================================
  def onL1Clicked(self):
    self.advanceAnatomyStep(self.l1Button, self.l2Button)
    self.currentAnatomyTarget = "L2"

  def onL2Clicked(self):
    self.advanceAnatomyStep(self.l2Button, self.l3Button)
    self.currentAnatomyTarget = "L3"

  def onL3Clicked(self):
    self.advanceAnatomyStep(self.l3Button, self.l4Button)
    self.currentAnatomyTarget = "L4"

  def onL4Clicked(self):
    self.advanceAnatomyStep(self.l4Button, self.l5Button)
    self.currentAnatomyTarget = "L5"

  def onL5Clicked(self):
    print("User is attempting to click L5...")
    
    self.tiltSpineModels(35)
    
    # 1. Only reveal the toggle posture button
    self.advanceAnatomyStep(self.l5Button, self.togglePostureButton)
    slicer.util.showStatusMessage("L5 Found! Please toggle the posture to continue.", 4000)
    
    self.currentAnatomyTarget = "Done" 
    
    if hasattr(self, 'spinalCanalModel') and self.spinalCanalModel.GetDisplayNode():
        self.spinalCanalModel.GetDisplayNode().SetVisibility(True)
    
    # 2. Drop the crosshairs so they can freely click the UI
    interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
    interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.ViewTransform)
  
  
  def onTogglePostureClicked(self):
    """Swaps the visibility of the neutral and extended spine STLs and updates the screen text."""
    self.isExtendedPosture = not getattr(self, 'isExtendedPosture', False)
    
    for key in self.anatomyModels:
      neu_model = self.anatomyModels.get(key)
      ext_model = self.extendedAnatomyModels.get(key)
      
      if neu_model and neu_model.GetDisplayNode():
        neu_model.GetDisplayNode().SetVisibility(not self.isExtendedPosture)
        
      if ext_model and ext_model.GetDisplayNode():
        ext_model.GetDisplayNode().SetVisibility(self.isExtendedPosture)
    
    if hasattr(self, 'spinalCanalModel') and self.spinalCanalModel.GetDisplayNode():
      self.spinalCanalModel.GetDisplayNode().SetVisibility(not self.isExtendedPosture)
      
    if hasattr(self, 'spinalCanalModel_Ext') and self.spinalCanalModel_Ext.GetDisplayNode():
      self.spinalCanalModel_Ext.GetDisplayNode().SetVisibility(self.isExtendedPosture)
        
    if hasattr(self, 'postureTextActor'):
      if self.isExtendedPosture:
        self.postureTextActor.SetInput("Posture: FLEXED")
        self.postureTextActor.GetTextProperty().SetColor(1.0, 0.6, 0.2) # Orange
      else:
        self.postureTextActor.SetInput("Posture: NEUTRAL")
        self.postureTextActor.GetTextProperty().SetColor(0.2, 0.8, 1.0) # Light blue
        
      # Force Slicer to instantly redraw the 3D window to show the text!
      slicer.app.layoutManager().threeDWidget(0).threeDView().scheduleRender()

    if getattr(self, 'currentAnatomyTarget', "") == "Done" and not self.anatomyCompleteButton.isVisible():
      self.anatomyCompleteButton.setVisible(True)
      
      # 1. Force the layout to move it to the top
      layout = self.anatomyCompleteButton.parentWidget().layout()
      if layout:
          layout.removeWidget(self.anatomyCompleteButton)
          layout.insertWidget(0, self.anatomyCompleteButton)
      
      slicer.app.processEvents()

  def onAnatomyCompleteClicked(self):
    """Automatically closes Anatomy, hides models, and opens the Calibration tab."""
    slicer.util.showStatusMessage("Anatomy Review Complete!", 4000)

    self.anatomyCollapsibleButton.setProperty('collapsed', True)
    self.calibrationCollapsibleButton.setProperty('collapsed', False)
    
    self.anatomyReviewCompleted = True 
    
    for modelNode in self.extendedAnatomyModels.values():
      if modelNode and modelNode.GetDisplayNode():
        modelNode.GetDisplayNode().SetVisibility(False)
  
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
    self.advanceProcedureStep(self.compStep2Button, self.procedureStopRecordingButton)

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

  def alignExtendedModelsToNeutral(self):
    """Calculates the 3D offset between the Neutral L5 and Extended L5, and aligns all extended models."""
    neu_L5 = self.anatomyModels.get("L5")
    ext_L5 = self.extendedAnatomyModels.get("L5")

    if not neu_L5 or not ext_L5 or not neu_L5.GetPolyData() or not ext_L5.GetPolyData():
      print("Warning: L5 models not loaded. Cannot align extended models.")
      return

    # 1. Calculate the exact Center of Mass for the Neutral L5
    comFilterNeu = vtk.vtkCenterOfMass()
    comFilterNeu.SetInputData(neu_L5.GetPolyData())
    comFilterNeu.Update()
    centerNeu = comFilterNeu.GetCenter()

    # 2. Calculate the exact Center of Mass for the Extended L5
    comFilterExt = vtk.vtkCenterOfMass()
    comFilterExt.SetInputData(ext_L5.GetPolyData())
    comFilterExt.Update()
    centerExt = comFilterExt.GetCenter()

    # 3. Calculate the distance (offset) between them in millimeters
    offsetX = centerNeu[0] - centerExt[0]
    offsetY = centerNeu[1] - centerExt[1]
    offsetZ = centerNeu[2] - centerExt[2]

    # 4. Create a Slicer Transform Node to hold this shift
    try:
      self.extendedAlignmentTransform = slicer.util.getNode('ExtendedAlignmentTransform')
    except slicer.util.MRMLNodeNotFoundException:
      self.extendedAlignmentTransform = slicer.vtkMRMLLinearTransformNode()
      self.extendedAlignmentTransform.SetName('ExtendedAlignmentTransform')
      slicer.mrmlScene.AddNode(self.extendedAlignmentTransform)

    # 5. Apply the offset to the transform matrix
    transformMatrix = vtk.vtkMatrix4x4()
    transformMatrix.SetElement(0, 3, offsetX)
    transformMatrix.SetElement(1, 3, offsetY)
    transformMatrix.SetElement(2, 3, offsetZ)
    self.extendedAlignmentTransform.SetMatrixTransformToParent(transformMatrix)

    # 6. Attach ALL extended models to this transform so the whole spine moves together!
    for ext_model in self.extendedAnatomyModels.values():
      if ext_model:
        ext_model.SetAndObserveTransformNodeID(self.extendedAlignmentTransform.GetID())
    
    if hasattr(self, 'spinalCanalModel_Ext') and self.spinalCanalModel_Ext:
      self.spinalCanalModel_Ext.SetAndObserveTransformNodeID(self.extendedAlignmentTransform.GetID())
        
    print(f"Successfully registered extended models to neutral L5. Shifted by: X:{offsetX:.1f}, Y:{offsetY:.1f}, Z:{offsetZ:.1f} mm")

  def setupTopPanel(self):
    buttonMinWidth = 48

    # 1. Create the layout
    self.topPanelLayout = qt.QGridLayout()
    self.sliceletPanelLayout.insertLayout(0, self.topPanelLayout)

    # 2. Load Button
    self.loadButton = qt.QPushButton()
    self.loadButton.setIcon(qt.QIcon(qt.QApplication.style().standardIcon(qt.QStyle.SP_DialogOpenButton)))
    self.loadButton.setMinimumWidth(buttonMinWidth)
    self.loadButton.toolTip = 'Load Volume'
    self.topPanelLayout.addWidget(self.loadButton, 0, 0)
    self.loadButton.connect('clicked()', self.onLoadButtonClicked)

    # 3. Save Button
    self.saveButton = qt.QPushButton()
    self.saveButton.setIcon(qt.QIcon(qt.QApplication.style().standardIcon(qt.QStyle.SP_DialogSaveButton)))
    self.saveButton.setMinimumWidth(buttonMinWidth)
    self.saveButton.toolTip = 'Save All Recordings'
    self.topPanelLayout.addWidget(self.saveButton, 0, 1)
    self.saveButton.connect('clicked()', self.saveAllRecordings)

    # --- Settings Button ---
    self.settingsButton = qt.QPushButton("Settings")
    self.settingsButton.setMinimumWidth(buttonMinWidth)
    self.settingsButton.toolTip = 'Open Settings Menu'
    self.topPanelLayout.addWidget(self.settingsButton, 0, 2)
    self.settingsButton.connect('clicked()', self.onOpenSettingsClicked)

    # 4. Record Button
    self.topRecordButton = qt.QPushButton("Start Recording")
    self.topRecordButton.setCheckable(True)
    self.topRecordButton.toolTip = 'Start/Stop Sequence Browser Recording'
    self.topPanelLayout.addWidget(self.topRecordButton, 0, 3)
    self.topRecordButton.connect('clicked()', self.onTopRecordButtonClicked)

    # 5. Logout Button
    self.logoutButton = qt.QPushButton("Logout")
    self.logoutButton.setMinimumWidth(buttonMinWidth)
    self.logoutButton.toolTip = 'Logout User'
    self.topPanelLayout.addWidget(self.logoutButton, 0, 4)
    self.logoutButton.connect('clicked()', self.onLogoutButtonClicked)

    # 6. Exit Button
    self.exitButton = qt.QPushButton()
    self.exitButton.toolTip = 'Exit'
    self.exitButton.setMinimumWidth(buttonMinWidth)
    self.exitButton.setIcon(qt.QIcon(qt.QApplication.style().standardIcon(qt.QStyle.SP_BrowserStop)))
    self.topPanelLayout.addWidget(self.exitButton, 0, 5)
    self.exitButton.connect('clicked()', self.onExitButtonClicked)

    # Push the buttons to the left side
    self.topPanelLayout.setColumnStretch(6, 1)

    # --- Initialize the Settings Window ---
    self.initSettingsDialog()

  def initSettingsDialog(self):
    """Builds the Settings pop-up window once in the background with full Guidelet features."""
    mainWindow = slicer.util.mainWindow()
    self.settingsWidget = qt.QDialog(mainWindow)
    self.settingsWidget.setWindowTitle('Lumbar Tutor Settings')
    self.settingsWidget.setModal(True) 
    self.settingsWidget.setMinimumWidth(450)

    # Main layout for the settings window
    self.settingsLayout = qt.QVBoxLayout(self.settingsWidget)
    self.settingsFormLayout = qt.QFormLayout()
    self.settingsLayout.addLayout(self.settingsFormLayout)

    # 1. UI Toggle: Show Full Slicer Interface
    self.showFullSlicerInterfaceButton = qt.QPushButton("Show 3D Slicer user interface")
    self.settingsFormLayout.addRow(self.showFullSlicerInterfaceButton)
    self.showFullSlicerInterfaceButton.connect('clicked()', self.onShowFullSlicerInterfaceClicked)
    self.showFullSlicerInterfaceButton.connect('clicked()', self.settingsWidget.hide) # Auto-close menu

    # 2. UI Toggle: Show Guidelet Fullscreen
    self.showGuideletFullscreenButton = qt.QPushButton("Show Guidelet in full screen")
    self.settingsFormLayout.addRow(self.showGuideletFullscreenButton)
    self.showGuideletFullscreenButton.connect('clicked()', self.onShowGuideletFullscreenButton)
    self.showGuideletFullscreenButton.connect('clicked()', self.settingsWidget.hide) # Auto-close menu

    # 3. Save Scene Button (Saves the entire Slicer workspace, not just the recording)
    self.saveSceneButton = qt.QPushButton("Save Guidelet scene (.mrb)")
    self.settingsFormLayout.addRow(self.saveSceneButton)
    self.saveSceneButton.connect('clicked()', self.onSaveSceneClicked)
    self.saveSceneButton.connect('clicked()', self.settingsWidget.hide)

    # 4. Save Directory Selector
    self.saveDirectoryLineEdit = ctk.ctkPathLineEdit()
    self.saveDirectoryLineEdit.filters = ctk.ctkPathLineEdit.Dirs
    self.saveDirectoryLineEdit.options = ctk.ctkPathLineEdit.ShowDirsOnly
    
    # Pre-fill with current parameter
    savedScenesDirectory = self.parameterNode.GetParameter('SavedScenesDirectory')
    if savedScenesDirectory:
        self.saveDirectoryLineEdit.currentPath = savedScenesDirectory
        
    self.settingsFormLayout.addRow("Save Directory:", self.saveDirectoryLineEdit)
    
    # Trigger an update when the user selects a new folder
    self.saveDirectoryLineEdit.connect('currentPathChanged(QString)', self.onSaveDirectoryPreferencesChanged)
    
    # 5. Add vertical spacing
    self.settingsLayout.addStretch(1)

    # 6. Close Button
    self.closeSettingsButton = qt.QPushButton("Close")
    self.closeSettingsButton.connect('clicked()', self.settingsWidget.hide)
    self.settingsLayout.addWidget(self.closeSettingsButton)

  def onSaveDirectoryPreferencesChanged(self, newPath):
    """Updates the parameter node and user settings when the save directory is changed."""
    # Tell the active session about the new path
    self.parameterNode.SetParameter('SavedScenesDirectory', newPath)
    
    # Tell Slicer to remember this preference the next time you open the module
    self.logic.updateSettings({'SavedScenesDirectory': newPath}, self.configurationName)
    print(f"Save directory updated to: {newPath}")

  def onOpenSettingsClicked(self):
    """Shows the Settings window when the top bar button is clicked."""
    # Ensure the directory path is visually up-to-date just in case it changed
    savedScenesDirectory = self.parameterNode.GetParameter('SavedScenesDirectory')
    if savedScenesDirectory:
        self.saveDirectoryLineEdit.currentPath = savedScenesDirectory
        
    self.settingsWidget.show()

  def onTopRecordButtonClicked(self):
    if self.topRecordButton.isChecked():
      # Visually indicate recording state
      self.topRecordButton.setText("Stop Recording")
      self.topRecordButton.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;") 
      
      # Start recording
      self.needleTutorSequenceBrowserNode = slicer.vtkMRMLSequenceBrowserNode()
      self.startSequenceBrowserRecording(self.needleTutorSequenceBrowserNode)      
    else:
      # Reset visuals
      self.topRecordButton.setText("Start Recording")
      self.topRecordButton.setStyleSheet("")
      
      # Stop recording
      self.stopSequenceBrowserRecording(self.needleTutorSequenceBrowserNode)

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

    self.emPositionLabel = qt.QLabel("Needle: --")
    self.emPositionLabel.setToolTip("Live NeedleToReference EM tracking position")
    self.calibrationLayout.addRow("EM position:", self.emPositionLabel)
    
    self.countdownLabel = qt.QLabel()
    self.calibrationLayout.addRow(self.countdownLabel)

    self.pivotSamplingTimer = qt.QTimer()
    self.pivotSamplingTimer.setInterval(500)
    self.pivotSamplingTimer.setSingleShot(True)
    
    self.isSpinCalibration = False


  def startNeedleTrackingDisplay(self):
    if not hasattr(self, 'needleToReference') or self.needleToReference is None:
      return

    self.stopNeedleTrackingDisplay()
    self.needleToReferenceObserver = self.needleToReference.AddObserver(
      slicer.vtkMRMLTransformNode.TransformModifiedEvent,
      self.onNeedleTransformModified
    )
    self.updateNeedleTrackingDisplay()


  def stopNeedleTrackingDisplay(self):
    if getattr(self, 'needleToReferenceObserver', None) is None:
      return
    try:
      self.needleToReference.RemoveObserver(self.needleToReferenceObserver)
    except (AttributeError, RuntimeError):
      pass
    self.needleToReferenceObserver = None


  def onNeedleTransformModified(self, caller, event):
    self.updateNeedleTrackingDisplay()


  def updateNeedleTrackingDisplay(self):
    if not hasattr(self, 'emPositionLabel') or not hasattr(self, 'needleToReference'):
      return

    matrix = vtk.vtkMatrix4x4()
    if not self.needleToReference.GetMatrixTransformToParent(matrix):
      self.emPositionLabel.setText("Needle: unavailable")
      return

    x = matrix.GetElement(0, 3)
    y = matrix.GetElement(1, 3)
    z = matrix.GetElement(2, 3)
    self.emPositionLabel.setText("Needle: X={0:.1f}  Y={1:.1f}  Z={2:.1f} mm".format(x, y, z))


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


  def saveAllRecordings(self):
    import os # Ensure os is available

    savedScenesDirectory = self.parameterNode.GetParameter('SavedScenesDirectory')
    if ( not os.path.exists(savedScenesDirectory) ):
      os.makedirs(savedScenesDirectory) # Make the directory if it doesn't already exist
    
    # Grab the user ID, default to UnknownUser if none is set
    currentUserId = getattr(self, 'userID', 'UnknownUser')
    
    recordingCollection = slicer.mrmlScene.GetNodesByClass( "vtkMRMLSequenceBrowserNode" )
    for nodeNumber in range( recordingCollection.GetNumberOfItems() ):
      browserNode = recordingCollection.GetItemAsObject( nodeNumber )
      base_node_name = browserNode.GetName() # Typically "Recording"
      
      # 1. Define what the start of our file looks like
      file_prefix = currentUserId + "-" + base_node_name + "-"
      
      # 2. Scan the directory to find the highest existing number for this user
      max_number = 0
      existing_files = os.listdir(savedScenesDirectory)
      
      for f in existing_files:
        if f.startswith(file_prefix) and f.endswith(".sqbr"):
          # Remove the prefix and the extension to isolate the number
          name_without_ext = os.path.splitext(f)[0]
          number_string = name_without_ext.replace(file_prefix, "")
          
          # If it's a valid number, check if it's the highest one we've seen
          if number_string.isdigit():
            num = int(number_string)
            if num > max_number:
              max_number = num
              
      # 3. Calculate the next logical number
      next_number = max_number + 1
      
      # 4. Generate the final sequential filename
      filename = file_prefix + str(next_number) + os.extsep + "sqbr"
      full_filepath = os.path.join( savedScenesDirectory, filename )
      
      slicer.util.saveNode( browserNode, full_filepath )
      print("Successfully saved recording to: " + full_filepath)


  def setupAnatomyPanel(self):
      import logging
      logging.debug('setupAnatomyPanel')

      self.anatomyCollapsibleButton = ctk.ctkCollapsibleButton()
      self.anatomyCollapsibleButton.setProperty('collapsedHeight', 20)
      self.anatomyCollapsibleButton.text = "Anatomy"
      self.anatomyCollapsibleButton.setMinimumWidth(380)
      self.sliceletPanelLayout.addWidget(self.anatomyCollapsibleButton)

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

      # --- Updated to explicitly match your L1-L5 STLs! ---
      self.l1Button = self.createWrappedButton("Click the L1 Vertebra")
      self.anatomyLayout.addWidget(self.l1Button)
      self.l1Button.setEnabled(False)

      self.l2Button = self.createWrappedButton("Click the L2 Vertebra")
      self.l2Button.setVisible(False)
      self.anatomyLayout.addWidget(self.l2Button)
      self.l2Button.setEnabled(False)

      self.l3Button = self.createWrappedButton("Click the L3 Vertebra")
      self.l3Button.setVisible(False)
      self.anatomyLayout.addWidget(self.l3Button)
      self.l3Button.setEnabled(False)

      self.l4Button = self.createWrappedButton("Click the L4 Vertebra")
      self.l4Button.setVisible(False)
      self.anatomyLayout.addWidget(self.l4Button)
      self.l4Button.setEnabled(False)

      self.l5Button = self.createWrappedButton("Click the L5 Vertebra")
      self.l5Button.setVisible(False)
      self.anatomyLayout.addWidget(self.l5Button)
      self.l5Button.setEnabled(False)

      self.togglePostureButton = self.createWrappedButton("Toggle Posture (Neutral / Extended)")
      self.togglePostureButton.setVisible(False)
      # Give it a nice blue color to stand out from the completion button
      self.togglePostureButton.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; border-radius: 4px; padding: 4px;")
      self.anatomyLayout.addWidget(self.togglePostureButton)
      
      self.anatomyCompleteButton = self.createWrappedButton("Anatomy Review Completed!\nClick to begin procedure.")
      self.anatomyCompleteButton.setVisible(False)
      self.anatomyCompleteButton.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; border-radius: 4px; padding: 4px;")
      self.anatomyLayout.addWidget(self.anatomyCompleteButton)
      
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
    """Disables current step, turns it green, and forces new steps to the absolute top."""
    # 1. Disable the current button and apply the green style
    currentButton.setEnabled(False)
    currentButton.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; border-radius: 4px;")

    # 2. Reveal the next button(s) and snap them to the top
    if nextButtons is not None:
      if not isinstance(nextButtons, list):
        nextButtons = [nextButtons]

      # Process in reverse so multiple buttons stay in logical order
      for btn in reversed(nextButtons):
        
        layout = btn.parentWidget().layout()
        if layout:
            layout.removeWidget(btn)    # 1. Pick the button up (Qt implicitly hides it here)
            layout.insertWidget(0, btn) # 2. Drop it exactly at the top (Index 0)
            
        btn.setVisible(True) # 3. Safely reveal it now that it is firmly placed!

    slicer.app.processEvents()
  
  def advanceAnatomyStep(self, currentButton, nextButtons=None):
    """Disables current step, turns it green, and pushes new steps to the top of the layout."""
    # 1. Disable the current button and apply the green style
    currentButton.setEnabled(False)
    currentButton.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; border-radius: 4px;")

    # 2. Reveal the next button(s) and snap them to the top
    if nextButtons is not None:
      if not isinstance(nextButtons, list):
        nextButtons = [nextButtons]

      # Process in reverse so multiple buttons stay in logical order (e.g., Step 2 above Step 3)
      for btn in reversed(nextButtons):
        btn.setVisible(True)
        
        # This dynamically finds the layout the button lives in and forces it to index 0 (the top)
        layout = btn.parentWidget().layout()
        if layout:
            layout.insertWidget(0, btn)
            
    slicer.app.processEvents()

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

    # 1. START RECORDING BUTTON (First Button)
    self.procedureStartRecordingButton = self.createWrappedButton("Start Recording")
    self.procedureLayout.addWidget(self.procedureStartRecordingButton)
    self.procedureStartRecordingButton.connect('clicked()', self.onProcedureStartRecordingClicked)
    # ==========================================
    # PHASE 1: PRE-PROCEDURE
    # ==========================================
    self.step1Button = self.createWrappedButton("Before Begining, the patient should be positioned in the lateral decubitus position or upright leaning forward withtheir feet supported, with their back facing the clinician. The patient's hips and knees should be flexed to open up the spaces between the vertebrae.")
    self.step1Button.setVisible(False) 
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

    # 2. STOP RECORDING BUTTON (Second to Last Button)
    self.procedureStopRecordingButton = self.createWrappedButton("Stop Recording")
    self.procedureLayout.addWidget(self.procedureStopRecordingButton)
    self.procedureStopRecordingButton.setVisible(False) # Hidden until revealed by the previous step
    self.procedureStopRecordingButton.connect('clicked()', self.onProcedureStopRecordingClicked)

    # 3. FINAL PROCEDURE BUTTON (Last Button)
    # (Assuming you have a final button like "Procedure Complete", it should be added after the stop button)

    self.compStep3Button = self.createWrappedButton("End of Study")
    self.compStep3Button.setVisible(False) 
    self.procedureLayout.addWidget(self.compStep3Button)
    
    self.procedureLayout.addStretch(1)

  def onProcedureStartRecordingClicked(self):
    """Starts the recording and advances to the first actual procedure step."""
    
    # 1. Sync with the top toolbar button to start recording safely
    if not self.topRecordButton.isChecked():
        self.topRecordButton.setChecked(True)
        try:
            self.onTopRecordButtonClicked() # This triggers the actual Sequence Browser recording
        except Exception as e:
            # If Slicer throws a background recording error, print it but DON'T stop the checklist!
            print(f"Silent recording error ignored: {e}") 

    # 2. Advance the checklist 
    self.advanceProcedureStep(self.procedureStartRecordingButton, self.step1Button)


  def onProcedureStopRecordingClicked(self):
    """Stops the recording, saves it, and advances to the completion step."""
    
    # 1. Sync with the top toolbar button to stop recording
    if self.topRecordButton.isChecked():
        self.topRecordButton.setChecked(False)
        try:
            self.onTopRecordButtonClicked() # Stops the Sequence Browser recording
        except Exception as e:
            print(f"Silent recording error ignored: {e}")

    # --- THE FIX: Trigger the save function automatically ---
    print("Recording stopped. Automatically saving files...")
    self.saveAllRecordings()

    # 2. Advance the checklist
    self.advanceProcedureStep(self.procedureStopRecordingButton, self.compStep3Button)

  def onCalibrationSetupPanelToggled(self, toggled):
    if toggled == False:
      return

    logging.debug('onCalibrationSetupPanelToggled: {0}'.format(toggled))
    self.navigationView = self.parameterNode.GetParameter( "CalibrationLayout" )
    self.updateNavigationView()

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
    if not browserNode:
        return
        
    try:
      sequenceNode = browserNode.GetMasterSequenceNode()
      if not sequenceNode:
          return # Exit if no sequence is present

      numDataNodes = sequenceNode.GetNumberOfDataNodes()    
      if numDataNodes < 2: # Cannot calculate FPS with one frame
          return
          
      startTime = float( sequenceNode.GetNthIndexValue( 0 ) )
      stopTime = float( sequenceNode.GetNthIndexValue( numDataNodes - 1 ) )
      
      duration = stopTime - startTime
      if duration > 0:
          frameRate = numDataNodes / duration
          browserNode.SetPlaybackRateFps( frameRate )
          
    except Exception as e:
      # Use a safe string format to avoid the Logging error
      logging.debug(f"setPlaybackRealtime failed: {str(e)}")

      
  def startSequenceBrowserRecording(self, browserNode):
    if (browserNode is None):
      return

    # Use the safe utility to get the logic
    # This will return None instead of throwing a RuntimeError if the module is missing
    sequenceBrowserLogic = slicer.util.getModuleLogic("SequenceBrowser")
    
    if not sequenceBrowserLogic:
        # Fallback: Maybe it's named differently in your specific Slicer build
        print("SequenceBrowser logic not found via standard name. Attempting to locate...")
        return # Exit gracefully instead of crashing
  
    # Indicate that this node was recorded, not loaded from file
    browserNode.SetName( slicer.mrmlScene.GetUniqueNameByString( "Recording" ) )
    browserNode.SetAttribute( "Recorded", "True" )
    # Create and populate a sequence browser node if the recording started
    browserNode.SetScene(slicer.mrmlScene)    
    slicer.mrmlScene.AddNode(browserNode)
    # Force Slicer to re-index the module before accessing its logic
    sequenceBrowserLogic = slicer.modules.sequencebrowser.widgetRepresentation().self().logic() if hasattr(slicer.modules, 'sequencebrowser') else slicer.modules.sequencebrowser.logic()
    # Alternatively, if that fails, use the direct accessor:
    sequenceBrowserLogic = slicer.util.getModuleLogic('SequenceBrowser')
        
    modifiedFlag = browserNode.StartModify()
    sequenceBrowserLogic.AddSynchronizedNode(None, self.needleToReference, browserNode)
    synchronizedNodes = [
      self.webcam1RGB,
      self.webcam1DEPTH,
      self.webcam0RGB,
      self.webcam0DEPTH,
    ]
    synchronizedNodeIds = set()
    for synchronizedNode in synchronizedNodes:
      if synchronizedNode and synchronizedNode.GetID() not in synchronizedNodeIds:
        sequenceBrowserLogic.AddSynchronizedNode(None, synchronizedNode, browserNode)
        synchronizedNodeIds.add(synchronizedNode.GetID())
    
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
