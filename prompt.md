
Phase 1

I have here an empty project with two folders. Client and server. Please follow the instructions bellow to build an app. Use the following checklist:
[ ] Both client and server will run on Ubutu Server
[ ] The app must be written in python
[ ] Create a conda environment named named UPS with python 3.13, acivate and use this conda environment for the development.
[ ] Everytime you add a python package to this environment create or update the requirements.txt file
[ ] The app must use P2P on a local network.
[ ] Clients must find the server by broadcasting on the local lan. They must keep retrying every 10 seconds with linear backoff up to 60 seconds. After that they will retry every 60 seconds.
[ ] After connecion with the server is established, clients must check if server is alive every 30 seconds plus a random number betewwen 1 and 30. If connection is lost they will resume the discovery process.
[ ] The server listens for broadcasts from the clients on UDP port 5225
[ ] Each client identifies itself on the server using the name of 
[ ] After connection is established, the server must be able to send messages to the clients.

Stop after Phase 1 is completed.
