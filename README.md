Installation steps:
1. Download the project and extract the files into the desktop, open vscode and select the “open this folder” option 
2. Select the Python interpreter
	a. I used a .conda python interpreter but if you already have one select the one that is already configured 
3. You may be missing some of the packages that are used in the program
	a. I included the requirement.txt file from my local machine, I use this environment for a few different classes, and it contains many packages not used at all in this project (they may cause some incompatibility issues) 
	b. The req.txt file is optional and if all the packages are installed just ignore the file
4. The application initializes the SQL database on the first run. Ensure the movies.db file exists in the project root. If it doesn’t, the application will make it automatically.
5. In VS Code:
    - pip install flask
    - pip install requests
6.  Run by pressing the "run" button on the top right
   ![image](https://github.com/user-attachments/assets/c55dc45e-763f-4fa7-b9af-f49780e93d82)
7. The follwing should appear in the terminal:
   ![image](https://github.com/user-attachments/assets/a16d1278-2ecc-4c26-b507-b35f3466da63)
8. Ctrl + click on the URL:
   ![image](https://github.com/user-attachments/assets/ce2090b3-3860-4c78-bbb4-55585e6c6b15)
9. You have now successfully run and started the application:
   ![image](https://github.com/user-attachments/assets/c404b7f0-36eb-4b7c-ac68-434d1439200b)
   
troubleshooting
* Deleting the db and restarting the application may resolve some issues 
