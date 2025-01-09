#  Surgical Planning for Brain Intervention(SPBI)
The software provides a series of functionalities to improve the safety and precision of brain intervention, including brain tissue segmentation, vessel segmentation, fiber tracking, and path planning. We collect healthy volunteer multimodal brain MRI data to present the functionalities.

## Requirements

We provide a requirements file requirements.txt. You can create a new conda environment or virtual environment and execute install the requirements using the following command.

```
pip install -r requirements.txt
```

## Fuctionalitiles

To demonstrate the functionalities of SIPB, multimodal brain MRI data were acquired from a healthy volunteer for surgical planning. Below is Flowchart of using SPBI for surgical planning of brain intervention.
![image](https://github.com/user-attachments/assets/b26b7903-68e7-42e4-a78b-43edce48c534)

## Brain Segmentation

For brain region segmentation, we utilized the 5ttgen function from the MRtrix3 algorithm library.
The result of brain segmentation depicts various components including grey matter (GM), subcortical grey matter (SGM) such as the amygdala and basal ganglia, white matter (WM), and cerebrospinal fluid (CSF).
![image](https://github.com/user-attachments/assets/ee0e0426-1d47-4b5d-b752-c871545f1a2e)

## Vessel Segmentation
For vessel segmentation, we used the hessian matrix filtering enhancement algorithm.
The image processing steps of vessel segmentation. (a) Segmentation Process. (b) VTK Volume Rendering. (c) Results: The final output is a 3D vessel reconstruction based on the processed and rendered image data.
![image](https://github.com/user-attachments/assets/4b8165b9-25be-43e6-9b04-fcca3a70d65c)

## Fiber tracking
For axonal fiber tract segmentation, we employed the DIPY toolkit. 
The complete image processing steps involved in fiber tracking are outlined below: (a) The ODF images. (b) GFA is utilized to evaluate the anisotropy of the diffusion tensor. (c) The final output consists of the tracked fiber bundles.
![image](https://github.com/user-attachments/assets/d4cd9733-3898-432f-a310-de2230ee0299)


