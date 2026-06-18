# iPhone Video to 3D Gaussian Splat

Training and rendering 3D Gaussian splats from iPhone video on Apple Silicon (M-series).

## Bigger picture of work

We have looked into gsplat-mlx-- the tier 3 metal shaders were not yet available.
Next we will look into opensplat.

## Formatting input dat
Here is how the incoming data is expected to be organized: 

my_scene/
├── images/                  <-- Put your extracted frames (.jpg or .png) here
│   ├── frame_0001.jpg
│   ├── frame_0002.jpg
│   └── ...
└── sparse/
    └── 0/                   <-- Your reference points and camera poses
        ├── cameras.bin      (or cameras.txt)
        ├── images.bin       (or images.txt)
        └── points3D.bin     (or points3D.txt)

OR

my_scene/
├── images/               <-- Put your source .jpg or .png frames here
│   ├── image_001.jpg
│   └── ...
├── cameras.json          <-- OpenMVG camera intrinsics
├── metadata.json         <-- Dataset metadata
├── points3d.json         <-- The sparse point cloud coordinates
└── poses.json            <-- Camera extrinsics (where the cameras are in 3D space)