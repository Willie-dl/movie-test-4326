README: Flask Movie Watchlist Project

Installation steps:
1. Download the project and extract the files into the desktop, open vscode and select the “open this folder” option 
2. Select the Python interpreter
	a. I used a .conda python interpreter but if you already have one select the one that is already configured 
3. You may be missing some of the packages that are used in the program
	a. I included the requirement.txt file from my local machine, I use this environment for a few different classes, and it contains many packages not used at all in this project (they may cause some incompatibility issues) 
	b. The req.txt file is optional and if all the packages are installed just ignore the file
4. The application initializes the SQL database on the first run. Ensure the movies.db file exists in the project root. If it doesn’t, the application will make it automatically.
5. Run the application
6. Open your web browser and navigate to:
	a. http://127.0.0.1:5000/
troubleshooting
* Deleting the db and restarting the application may resolve some issues 

