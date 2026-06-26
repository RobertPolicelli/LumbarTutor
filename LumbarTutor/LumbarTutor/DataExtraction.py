import slicer
import vtk
import os
import csv
import time
#exec(open(r"C:\Users\hernia\Documents\Denesh\LumbarTutor\LumbarTutor\LumbarTutor\DataExtraction.py").read())
# --- CONFIGURATION ---
SAVE_DIRECTORY = os.path.expanduser("~/Documents")
# ---------------------

def get_world_polydata(modelNode):
    """Safely extracts the PolyData of a model in global World coordinates."""
    polydata = modelNode.GetPolyData()
    transformNode = modelNode.GetParentTransformNode()
    
    if transformNode:
        matrix = vtk.vtkMatrix4x4()
        transformNode.GetMatrixTransformToWorld(matrix)
        transform = vtk.vtkTransform()
        transform.SetMatrix(matrix)
        
        tFilter = vtk.vtkTransformPolyDataFilter()
        tFilter.SetInputData(polydata)
        tFilter.SetTransform(transform)
        tFilter.Update()
        return tFilter.GetOutput()
    
    return polydata

def extract_and_save():
    print("Starting manual data extraction and metric calculation...")
    
    # 1. Grab the Sequence Browser and Transform
    try:
        browserNode = slicer.util.getNode('Recording')
        trackedTransformNode = slicer.util.getNode('NeedleToReference')
    except slicer.util.MRMLNodeNotFoundException:
        print("Error: Required tracking nodes not found. Is the data loaded?")
        return

    sequenceNode = browserNode.GetMasterSequenceNode()
    if not sequenceNode:
        print("Error: No master sequence node found.")
        return

    numDataNodes = sequenceNode.GetNumberOfDataNodes()
    if numDataNodes == 0:
        print("Error: No recorded frames found in the sequence.")
        return

    # 2. Setup the Models for Spatial Math
    try:
        targetNode = slicer.util.getNode('L4_L5_TargetSpace')
        nonAnatomyNode = slicer.util.getNode('NonAnatomyTabModel')
    except slicer.util.MRMLNodeNotFoundException:
        print("Error: Required STL models not found in the scene.")
        return

    # Build an OBBTree for the L4/L5 space AND calculate which way faces point
    target_pd = get_world_polydata(targetNode)
    
    normalsFilter = vtk.vtkPolyDataNormals()
    normalsFilter.SetInputData(target_pd)
    normalsFilter.ComputeCellNormalsOn()  # We need the normal for each triangle
    normalsFilter.ComputePointNormalsOff()
    normalsFilter.ConsistencyOn()         # Force all normals to point outward
    normalsFilter.Update()
    target_pd_with_normals = normalsFilter.GetOutput()

    target_obb = vtk.vtkOBBTree()
    target_obb.SetDataSet(target_pd_with_normals)
    target_obb.BuildLocator()
    
    # Store the normals to check them later
    cell_normals = target_pd_with_normals.GetCellData().GetNormals()

    # Find the Front Plane of the nonAnatomy model
    nonAnat_pd = get_world_polydata(nonAnatomyNode)
    bounds = nonAnat_pd.GetBounds() 
    front_y = bounds[3] 

    # >>> THIS IS THE LINE THAT WAS MISSING <<<
    extracted_data = []
    
    # Tracking Variables for Metrics
    times_entered_target = 0
    time_first_entered = None
    was_inside_target = False
    prev_pos = None 

    times_crossed_front = 0
    was_in_front = None

    # 3. Loop and Extract
    for i in range(numDataNodes):
        browserNode.SetSelectedItemNumber(i)
        timestamp = float(sequenceNode.GetNthIndexValue(i))

        matrix = vtk.vtkMatrix4x4()
        trackedTransformNode.GetMatrixTransformToWorld(matrix)
        
        x = matrix.GetElement(0, 3)
        y = matrix.GetElement(1, 3)
        z = matrix.GetElement(2, 3)
        curr_pos = (x, y, z) 

        # --- Metric Logic: L4/L5 Entry ---
        pts = vtk.vtkPoints()
        # Check if currently inside (Odd number of raycast hits)
        target_obb.IntersectWithLine(curr_pos, (x, y + 5000.0, z), pts, None)
        is_inside_target = (pts.GetNumberOfPoints() % 2 == 1)

        if is_inside_target and not was_inside_target:
            if prev_pos is not None:
                # The needle just crossed the boundary. Trace the path from the last frame.
                intersect_pts = vtk.vtkPoints()
                intersect_cells = vtk.vtkIdList()
                
                # Extend the previous position slightly backwards to ensure the mathematical 
                # line crosses the STL boundary perfectly
                direction = [curr_pos[j] - prev_pos[j] for j in range(3)]
                extended_prev = [prev_pos[j] - direction[j]*2 for j in range(3)]
                
                target_obb.IntersectWithLine(extended_prev, curr_pos, intersect_pts, intersect_cells)
                
                # If we hit a wall, check which way that wall is facing
                if intersect_cells.GetNumberOfIds() > 0 and cell_normals:
                    first_cell_id = intersect_cells.GetId(0)
                    normal = cell_normals.GetTuple3(first_cell_id)
                    
                    # +Y is "Front" (towards the skin). We use > 0.1 to avoid 
                    # accidentally counting side-walls that are slightly imperfect.
                    if normal[1] > 0.1:
                        times_entered_target += 1
                        if time_first_entered is None:
                            time_first_entered = timestamp
                    else:
                        print(f"Note: Ignored entry at {timestamp:.2f}s - Hit a side or back wall (Normal Y: {normal[1]:.2f})")
            
        was_inside_target = is_inside_target
        prev_pos = curr_pos 

        # --- Metric Logic: Front Plane Crossing ---
        is_in_front = (y > front_y)
        if was_in_front is not None and is_in_front != was_in_front:
            times_crossed_front += 1
        was_in_front = is_in_front

        # Save frame data
        extracted_data.append({
            'time_sec': timestamp,
            'x_mm': x,
            'y_mm': y,
            'z_mm': z,
            'in_target': int(is_inside_target),
            'in_front_of_plane': int(is_in_front)
        })

    # 4. Save to CSV
    if not os.path.exists(SAVE_DIRECTORY):
        os.makedirs(SAVE_DIRECTORY)

    filename = f"NeedleTracking_{time.strftime('%Y%m%d-%H%M%S')}.csv"
    filepath = os.path.join(SAVE_DIRECTORY, filename)

    if not extracted_data:
        print("Error: No data was extracted. Check if the sequence contains valid frames.")
        return

    keys = extracted_data[0].keys()
    with open(filepath, 'w', newline='') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(extracted_data)

    # 5. Output Results
    print("\n--- EXTRACTION COMPLETE ---")
    print(f"Data successfully saved to: {filepath}")
    print(f"Total Frames Analyzed: {len(extracted_data)}")
    print("\n--- KINEMATIC METRICS ---")
    print(f"Times Entered L4/L5 Target Space (Front Wall Only): {times_entered_target}")
    
    if time_first_entered is not None:
        print(f"Time to First Entry (sec): {time_first_entered:.2f}")
    else:
        print("Time to First Entry (sec): N/A (Never entered)")
        
    print(f"Times Crossed Front Plane: {times_crossed_front}")
    print("---------------------------\n")

# Automatically run the function when the script is executed
extract_and_save()