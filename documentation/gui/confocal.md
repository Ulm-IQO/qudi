# Confocal GUI {#confocalgui}

By pressing `Load confocalgui` the Confocal GUI opens:

![](:software:qudi:documentation:modules:gui:confocal-capture-20150621112916-058-0.png)

## File

On the top left side is the `File` button. By clicking on it one can choose between `Save XY data`, `Save XZ data`, `Save XY image + data`,`Save XZ image + data` and `Exit`.

### Save XY data

The raw data is saved in two files. In the `confocal_xy_data` file the raw data is displayed along with their corresponding x,y,z-corrdinates:

![]( :software:qudi:documentation:modules:gui:neue_bitmap3.png?500 )


The `confocal_xy_image` file saves the raw data of the image which is displayed in th GUI. So every data point corresponds to the value of one pixel of the image. As it is shown below first the data block corresponding to the first row is displayed, then the second row and so on...

![]( :software:qudi:documentation:modules:gui:neue_bitmap2.png?500 )


The location where you can find the two files is:
 C:\Data\YEAR\MONTH\DAY\Confocal\

The saving settings can be changed in the `Settings` menu.

### Save XZ data


Does the same as `Save XY data` with XZ.


### Save XY image + data

`Save XY image + data` saves the XZ image as a `.png` and as a `.svg`. Furthermore it saves the raw data as described in `Save XY data`.

### Save XZ image + data

Does the same as `Save XY image + data` with XZ.

### Exit

`Exit` closes the Confocal GUI.


## Option

In the `Options` menu one can change the `Settings` and the `Optimiser Settings`.

## Settings

After choosing `Settings` the following window shows up: 

![](:software:qudi:documentation:modules:gui:confocal-capture-20150621122712-942-0.png)

### Clock frequency

Here one can change the frequency of the clock which is used to scan.

### Return slowness

Here one can change the velocity of the scanner after it reaches the end of a line to go back to the beginning of the next line.

### Fixed Aspect Ratio XY Scan

Here one can you choose how the XY image is displayed in the GUI. If the box is checked then the aspect ratio of the image will match the real aspect ratio. For example for a 100 x 50 scan, the image will have  a 2:1 aspect ratio. If it is not checked the images will be quadratic.

### Fixed Aspect Ratio Depth Scan

Does the same as described in `Fixed Aspect Ratio XY Scan` for the Depth Scan.

### Save ImageScene also as png file

If this box is checked an additional png image will be saved which also contains the coordinate axes and the colorbar.

### Save pure Image as png

If this box is checked only the pure image will be saved. If it is unchecked also the coordinate axes and the colorbar will be saved.

### Switch off hardware

If one wants to change from the Qudi to the "old" pi3diamond software one should use this button to disconnect Qudi from the hardware.


## Optimiser - Settings

After choosing `Optimiser - Settings` the following window shows up:

![](:software:qudi:documentation:modules:gui:confocal-capture-20150621124317-900-0.png)

Here one can change the range and the stepsize of the optimiser image as well as the count frequency and the return slowness (description see `Settings` above).

## View

Here one can you choose to display or close the four dockable elements (see below) of the Confocal GUI.

## Dockable elements

### XY Scan

![](:software:qudi:documentation:modules:gui:confocal-capture-20150621130715-502-3.png)

Here the image of the XY scan is displayed. On the right side there is a controlable [[colorbar]]. On the bottom there are five radiobuttons. By chlicking `Scan XY` one can start a XY scan. The scan can be stopped at any time by chlicking `Ready`. After that a new scan can be started by clicking `Scan XY` again or the stopped scan can be continued by choosing `Continue XY`. By clicking `Depth Scan` the depth scan can be started (can be stopped by choosing `Ready` but can not be continued yet) and by clicking `Optimise position` the position of the crosshair is optimised in a way that after the scan the crosshair is positioned at the location of the maximum counts.

### Depth Scan

![](:software:qudi:documentation:modules:gui:confocal-capture-20150621130426-048-2.png)

Here the image of the depth scan is displayed. The cursor is moveable via mouse or `Scan control`. The working principle is the same as for the 'XY scan' described above.

### Optimiser

![](:software:qudi:documentation:modules:gui:confocal-capture-20150621125856-031-1.png)

Here one can find a XY Scan in the proximity of the crosshair a Depth Scan including a fit as well as the exact coordinates of the crosshair.

### Scan control

![](:software:qudi:documentation:modules:gui:confocal-capture-20150621125309-125-0.png)

In the `scan control` element one can change the resolution, the scan range and the position of the cursor. All boxes are tabable and controlable via keyboard mouse wheel and arrow keys. The cursor position is additionally changeable with sliders.


