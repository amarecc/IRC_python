import socket
import sys
import threading
import select

s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
s.bind(("", 7778))

listeClients = [ s ]
dicoClients = {}
connectedClients = []
channelDico = dict([("", "")])
clientIsInChannel = {}

clientChannel = {}

s.listen(1)

def usage(sc, type):
	strToSend = ""
	if type == "MSG":
		strToSend += "MSG <channel> <message>"

	elif type == "QUIT":
		strToSend += "QUIT <message>"
	
	elif type == "KILL":
		strToSend += "KILL <nickname> <message>"

	elif type == "default":
		strToSend += "<cmd> <arg>"
	
	formatAndSendMessage(sc, "usage", strToSend)

def formatAndSendMessage(destSocket, messageType, message):
	destSocket.sendall(("["+messageType+"] " + message + "\n").encode("utf-8"))

def sendMessage(sc, message, dest, channel):
	# Different behavior if there is one word or many
	if len(message) > 1:
		messageStr = " "
		messageStr = messageStr.join(message)
	else:
		messageStr = message[0]


	if dest == None and channel != None:
		if channel == clientChannel[sc]:	
			for client in listeClients:
				# Check if client is in the channel
				if client is not sc and client is not s and client in channelDico[channel]:
					formatAndSendMessage(client, dicoClients[sc], messageStr)
		else:
			formatAndSendMessage(sc, "server","You're not in the channel")
	
	# Default behavior for kick, quit etc... (sending message on a certain person)
	else:
		formatAndSendMessage(dest, dicoClients[sc], messageStr)

# Change nickname & replace the client Id by the nickname
def changeNickName(sc, nickname):
	print("client " + dicoClients[sc] + " =>  \""+nickname+"\"")

	dicoClients[sc] = nickname
	connectedClients.append(nickname)

# Close the client connection and clean the structures
def leaveServer(sc, message):
	if len(message) > 0:
		sendMessage(sc, [message], None, clientChannel[sc])

	if clientChannel[sc] != "":
		partChannel(sc, clientChannel[sc])
	sc.close()
	print("client disconnected \""+dicoClients[sc]+"\"")

	connectedClients.remove(dicoClients[sc])
	listeClients.remove(sc)
	del dicoClients[sc]

# Show connected people
def showConnected(sc):
	newStr = " "
	strToSend = newStr.join(connectedClients)
	formatAndSendMessage(sc, "server", strToSend)

# kill a client
def killClient(sc, nickname, message):
	for key, value in dicoClients.items():
		if value == nickname:
			sendMessage(sc, message, key, None)
			leaveServer(key, "")
			break

def joinChannel(sc, channel):
	if clientIsInChannel[sc] == False:
		# Create chan & add client on it
		if channel not in channelDico:
			channelDico[channel] = dict([(sc, dicoClients[sc])])
		else:
			channelDico[channel][sc] = dicoClients[sc]

		clientIsInChannel[sc] = True
		clientChannel[sc] = channel
	else:
		formatAndSendMessage(sc, "server", "You're already in a channel")
	
# Eject the client of the channel and destroy if needed
def partChannel(sc, channel):
	if channel in channelDico:
		if sc in channelDico[channel]:
			del channelDico[channel][sc]
			if len(channelDico[channel]) == 0:
				del channelDico[channel]
		clientIsInChannel[sc] = False
		clientChannel[sc] = ""
	
	elif channel == "":
		formatAndSendMessage(sc, "server", "You're not in a channel")
	else:
		formatAndSendMessage(sc, "server", "You're not in this channel")

# List all the channel
def listChannel(sc):
	strToSend = "[channel] "
	for key, value in channelDico.items():
		if key != "":
			strToSend += str(key)
	
	strToSend += "\n"
	sc.sendall(strToSend.encode("utf-8"))

def kickClientFromChannel(sc, nickname):
	# Check if client have the right to kick the target
	if clientIsInChannel[sc]:
		for targetSocket, targetNickname in channelDico[clientChannel[sc]].items():
			if targetNickname == nickname:
					partChannel(targetSocket, clientChannel[sc])
					formatAndSendMessage(targetSocket, "server", "You've been kicked by "+dicoClients[sc])
					break
	else:
		formatAndSendMessage(sc, "server","You can't kick someone, you're not in a channel")


# Main function to manage data received by the client
def handle(sc):
	answer = sc.recv(1500)
	if len(answer) == 0:
		listeClients.remove(sc)
		sc.close()
	else:
		answer = answer.decode("utf-8")
		commandList = answer.split()
		if len(commandList) >= 1:
			if commandList[0] == "MSG":
				if len(commandList) > 2:
					sendMessage(sc, commandList[2:], None, commandList[1])
				else:
					usage(sc, "MSG")
			
			elif commandList[0] == "NICK":
				changeNickName(sc, commandList[1])

			elif commandList[0] == "WHO":
				showConnected(sc)

			elif commandList[0] == "JOIN":
				joinChannel(sc, commandList[1])

			elif commandList[0] == "PART":
				partChannel(sc, clientChannel[sc])

			elif commandList[0] == "LIST":
				listChannel(sc)

			elif commandList[0] == "KICK":
				kickClientFromChannel(sc, commandList[1])
			
			elif commandList[0] == "QUIT":
				if len(commandList) > 1:
					leaveServer(sc, commandList[1])
				else:
					usage(sc, "QUIT")
			
			elif commandList[0] == "KILL":
				if len(commandList) < 3:
					usage(sc, "KILL")
				else:
					killClient(sc, commandList[1], commandList[2:])
			else:
				usage(sc, "default")
			
		else:
			usage(sc, "default")

def formatAdresse(adress, port):
	newStr = "\"127.0.0.1:"+ str(port) + "\""

	return newStr

while True:
	l, a, b = select.select(listeClients, [], [])

	for socket in l:

		# New client connected
		if socket is s:
			sc, adr = socket.accept()
			listeClients.append(sc)

			adr, port, x, y = sc.getpeername()
			clientId = formatAdresse(adr, port)
			print("client connected "+clientId)

			dicoClients[sc] = clientId
			channelDico[""] = dicoClients
			clientIsInChannel[sc] = False
			clientChannel[sc] = ""


		# New data received
		else:
			handle(socket)

s.close()