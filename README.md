# Study localwebui
A localized, offline study environment featuring an interactive glassmorphism UI, real-time volumetric caustics, and integrated vector-drawing tools.

## 🖥️ Interface & Visuals
<img width="1919" height="1076" alt="Demo_image" src="https://github.com/user-attachments/assets/3b041b82-a946-4fbe-af76-6e18bbe28582" />


### 🌊 Interactive Fluid Motion & PDF Shredding



https://github.com/user-attachments/assets/6c32367d-5ef2-4a5b-b00c-e96088fe3b3a



### Day & Night Celestial Cycle
The environment automatically syncs with your system clock, transitioning from a warm neon sun during the day to an icy moon at night.

## 🚀 Core Features
* **Smart PDF Parsing:** Automatically shreds heavy PDF documents down to discrete, trackable page images.
* **Vector Canvas HUD:** Draw force vectors, highlights, and custom physics annotations directly onto question images.
* **Gamification:** Track your study streaks, earn XP, and unlock badges based on your daily consistency.
* **Offline Security:** Runs 100% locally on your machine with disabled browser inspector overrides.

## ⚙️ Installation & Setup Guide

If you are new to this platform, follow these simple steps to get your local environment running. No coding experience is required!

**Step 1: Download the Files**
1. Click the green **`<> Code`** button at the top of this repository.
2. Select **`Download ZIP`**.

**Step 2: Unblock the ZIP (Important for Windows)**
Because you downloaded this from the internet, Windows might block the batch file from running. 
* Right-click the downloaded `.zip` file and select **Properties**.
* Look at the bottom of the General tab. If you see a security warning, check the box that says **Unblock**.
* Click **Apply**, then **OK**, and extract the ZIP folder.

**Step 3: Run the Application**
1. Open the extracted folder and double-click the **`Initiate_Study_Work.bat`** file. 
2. *Note: The very first time you run this, it will take a few moments to automatically install the required background engines (like Flask and PyMuPDF). Just let the black terminal window run.*

**Step 4: Select Your Study Folder**
1. Once the server starts, it will automatically open a new tab in your web browser.
2. Select the main folder on your computer where you keep your study PDFs and images. The app will instantly map your files and build your grid.


## ⌨️ Keyboard Shortcuts
* **Spacebar:** Mark a question/page as 'Done' (earns XP).
* **F Key:** Flag a target for review.
* **Left/Right Arrows:** Quickly flip between document pages or images.
