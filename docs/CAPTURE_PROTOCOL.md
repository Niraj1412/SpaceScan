# Stock capture protocol (one page)

Use this page literally. Total time for a three-room property is normally 4–8 minutes.

## Before entering

1. Install **Record3D — 3D Videos** by Marek Simonik from the Apple App Store. In the submission notes, record the app version shown on the phone. Record3D supports LiDAR capture; its free trial permits three recordings.
2. Clean the rear camera/LiDAR glass. Set brightness above 50%, disable Low Power Mode, and ensure at least 2 GB free storage.
3. Open curtains or switch on lights. Do not move furniture. Keep people and pets out.
4. Put a removable start marker on the floor at the entrance. This is the loop-closure anchor.

## LiDAR tier — iPhone Pro/Pro Max with LiDAR

1. Open Record3D, select the rear **LiDAR** sensor, and start a new 3D Video.
2. Hold the phone in portrait at chest height (about 1.3–1.5 m). Move slowly; do not change orientation mid-capture.
3. Start over the marker. Pause for two seconds while facing into the first room.
4. Walk the room perimeter clockwise, 0.5–1.5 m from each wall. Point at the wall/floor junction, then make one deliberate pass aimed at the wall/ceiling junction.
5. Pause one second at every door/window. Keep each opening fully visible; do not stand inside the doorway.
6. Continue through connectors without stopping the recording. Enter every room and trace its perimeter. Revisit each connecting doorway from both sides.
7. Finish on the same marker, facing the same direction, and hold still for two seconds. A closed loop is mandatory for drift correction.
8. Avoid fast turns, featureless close-up walls, direct mirrors, bright sun through glass, and distances over 4 m. For mirrors/glass, scan obliquely from both sides; never treat reflected geometry as coverage.
9. Save the original recording. Export/copy the raw Record3D folder without transcoding. It must include RGB video, uint16 depth frames, confidence frames, poses, and intrinsics. Zip that folder and transfer it by AirDrop, Files, cable, or Drive.

## Video tier — any iPhone 15 or newer

Use the native Camera app at 1080p/30 fps, 1× lens, no cinematic mode. Follow the identical start, perimeter, doorway, ceiling, and return path above. Record one continuous clip; do not pause, zoom, or switch lenses. Transfer the original `.MOV`/`.MP4`, not a messaging-app copy.

## Photo tier — any iPhone 15 or newer

Create one folder per room. Take 8 landscape photos per room: four from corners aimed diagonally and four centred on walls. Include the complete floor/wall and wall/ceiling junctions; make each doorway visible in both connected room folders. Use 1× lens and normal Photo mode; do not use panorama, portrait mode, zoom, screenshots, or edited copies. Name folders in walking order (`01_entry`, `02_hall`, `03_bedroom`). Transfer originals with metadata.

## Handoff check

- LiDAR: one raw capture folder; video: one original clip; photos: 2–8 originals in every room folder.
- Include `capture_notes.txt`: phone model, iOS version, Record3D version (if used), tier, room order, known mirrors/glass, and anything missed.
- Run exactly: `spacescan <handoff-path> --output runs/<capture-name>`.

