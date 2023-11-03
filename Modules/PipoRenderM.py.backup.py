import os
import maya.cmds as mc
import pymel.core as pm
import sys
import pickle
import yaml
import discord 
import asyncio
import glob
import scandir

from functools import partial
from datetime import datetime


class PipelineRenderApplication:

	def import_from_shaderlibrary_function(self, event):
		#check the selection in shaderlist
		shader_selection = mc.textScrollList(self.saved_shader_textscrolllist, query=True, si=True)
		if (type(shader_selection)!= list) or (len(shader_selection) == 0):
			mc.error("You have to select a shader to import!")
			return 

		#get the path of the project
		project_path = mc.textField(self.project_label, query=True, text=True)

		for shader in shader_selection:
			#check if the shader exists in the folder
			if os.path.isfile(os.path.join(project_path, "PipelineManagerData/shaderDataBase/%s"%shader))==False:
				mc.warning("Shader skipped [%s]"%shader)
				continue
			else:
				try:
					mc.file(os.path.join(project_path, "PipelineManagerData/shaderDataBase/%s"%shader), i=True)
				except:
					mc.warning("Impossible to import the shader [%s]"%shader)
					continue





	def detect_missing_frames_function(self, event):
		#get all required informations
		#frame range
		starting_frame = mc.intField(self.render_startingframe_textfield, query=True, value=True)
		ending_frame = mc.intField(self.render_endingframe_textfield, query=True, value=True)

		if (self.default_render_nomenclature == None) or (self.root_render_folder == None):
			mc.error("You have to check the render folder before checking missing frames!\nImportant informations are missing!")
			return


		"""
		file dictionnary
			folder
				files
				files
			folder
				files
				files
		"""
		file_dictionnary = {}
		log_list = {
			"nomenclatureChecking":[],
			"missingFrames":[],
			"noSizeFile":[],
			"lightFiles":[],
			"averageRenderSize":"None"
		}

		


		for root_folder in self.root_render_folder:
			for element in os.listdir(root_folder):
				#check that it's a folder and not a file!
				if os.path.splitext(element)[1] == "":
					file_list = os.listdir(os.path.join(root_folder, element))
					
					"""
					check the syntax of each file in the folder
					"""
					for file in file_list:
						splited_file = os.path.splitext(file)[0].split(self.default_render_spliting_method)
						if len(splited_file) != len(self.default_render_nomenclature):
							mc.warning("File skipped because of wrong nomenclature [%s]"%file)

							#update error dictionnary
							nomenclature_checking = log_list["nomenclatureChecking"]
							nomenclature_checking.append(file)
							log_list["nomenclatureChecking"]=nomenclature_checking
							continue
						else:
							#check the index of the frame
							#check the index of the content
							content = splited_file[self.default_render_nomenclature.index("[content]")]
							frame = splited_file[self.default_render_nomenclature.index("[frame]")]
							
							if content not in file_dictionnary:
								file_dictionnary[content] = [[file, frame]]
							else:
								content_list = file_dictionnary[content]
								content_list.append([file, frame])
								file_dictionnary[content] = content_list

		if len(list(file_dictionnary.keys())) == 0:
			mc.error("No frame detected!")
			return


		"""
		for each frame check the syntax to get the frame
		create a loop that is frame range long --> check for missing frames
		for existing frames check the size of the file
		"""
		if (starting_frame >= ending_frame):
			mc.error("Wrong frame range in fields!")
			return



		frame_range = list(range(starting_frame, ending_frame))
		print(frame_range)


		"""
		need to compare the actual frame list (range list) with the files frames list
			import os
			file_size = os.path.getsize('d:/test_file.jpg')
			print("File Size is :", file_size)
		"""
		average_size = 0
		lower_size = 0


		

		for key, value in file_dictionnary.items():
			frame_list = []
			for file in value:
				#print(file[0])
				#list all frames
				#check the size of the file on the hardrive
				#print(file[0])
				
				for root_folder in self.root_render_folder:
					for root, dirs, files in os.walk(root_folder):
						for f in files:
							if f == file[0]:
								#checking size of the file
								file_size = os.path.getsize(os.path.join(root, f))

								if file_size == 0:
									no_size_file_list = log_list["noSizeFile"]
									no_size_file_list.append(f)
									log_list["noSizeFile"] = no_size_file_list
								else:
									if average_size == 0:
										average_size = file_size
										lower_size = (average_size * 95) / 100
										
									else:
										average_size = (average_size + file_size) / 2
										lower_size = (average_size * 80) / 100
										

									if (file_size <= lower_size):
										variable_frame_list = log_list["lightFiles"]
										variable_frame_list.append("%s : [%s]"%(f, file_size))
										log_list["lightFiles"] = variable_frame_list
									
									





				frame_list.append(int(file[1]))

			#print(frame_list)
			for frame in frame_range:
				#print(frame, frame in frame_list)
				if (frame in frame_list) == False:
					missing_frame_list = log_list["missingFrames"]
					missing_frame_list.append("%s : [%s]"%(key, frame))
					log_list["missingFrames"] = missing_frame_list
		log_list["averageRenderSize"] = average_size

		


		#create informations 
		#send to local textscrolllist

		"""
		EMOJIS
			:face_with_symbols_over_mouth:
		"""
		textscrolllist_info = []
		self.discord_message = "##########################################\n:loudspeaker:**RENDER CHECKING**:warning:\n##########################################\n"
		for key, value in log_list.items():

			self.discord_message += "\n\n__%s__\n"%key
			textscrolllist_info.append("\n")
			textscrolllist_info.append(key)

			if type(value) == list:
				for v in value:
					self.discord_message += "\t_%s_\n"%str(v)
					textscrolllist_info.append(str(v))
			else:
				textscrolllist_info.append("_%s_"%str(value))
				self.discord_message += "\t%s\n"%str(value)
		mc.textScrollList(self.render_renderlog_textscrolllist, edit=True, removeAll=True, append=textscrolllist_info)


		"""
		formatting text for discord message
		"""
		if mc.checkBox(self.render_checking_checkbox, query=True, value=True) == True:

			#try to get discord server informations in dictionnary
			self.token = self.additionnal_settings["discordBotToken"]
			self.channel_id = self.additionnal_settings["discordChannelId"]

			if (self.token == None) or (self.channel_id == None):
				mc.error("Missing informations to send messages on discord server!")
				return
			else:
				asyncio.run(self.send_discord_message_function())




	async def send_discord_message_function(self):
	    intents = discord.Intents.default()
	    intents.typing = False
	    intents.presences = False

	    client = discord.Client(intents=intents)

	    @client.event
	    async def on_ready():
	        print(f"We have logged in as {client.user}")
	        guild = client.get_guild(self.channel_id)
	        channel = discord.utils.get(guild.channels, name="général")
	        await channel.send(self.discord_message)
	        await client.close()

	    try:
	        await client.start(self.token)
	        # Ajouter une pause pour attendre que le bot soit prêt avant d'envoyer le message
	        await asyncio.sleep(5)
	    except KeyboardInterrupt:
	        print("Bot closed!")
	    except Exception as e:
	        print(f"An error occurred: {e}")






	


					



	






	def save_in_shaderlibrary_function(self, event):
		#get selection in current shader textscrolllist
		selection = mc.textScrollList(self.current_shader_textscrolllist, query=True, si=True)

		if (selection == None) or (len(selection)==0):
			mc.error("You have to select a shader to save!")
			return 
		else:
			
			#detect all shaders connections to select all nodes to save!
			self.all_connexions = []

			for shader in selection:
				"""
				for each shader selected
				get the shading engine to select
				"""
				shading_engine = mc.listConnections(shader, type="shadingEngine")

				if shading_engine == None:
					mc.warning("Shader skipped, Impossible to find shading engine [%s]"%shader)
				else:
					if (shading_engine in self.all_connexions)==False:
						self.all_connexions += shading_engine
			self.all_connexions += selection 

			#select element (NO EXTAND)
			#export the new file in the pipeline
			mc.select(self.all_connexions, r=True, ne=True)
			
			try:
				#create all required folders
				os.makedirs(os.path.join(mc.textField(self.project_label, query=True, text=True), "PipelineManagerData/shaderDataBase/"), exist_ok=True)
				mc.file(os.path.join(mc.textField(self.project_label, query=True, text=True), "PipelineManagerData/shaderDataBase/shader_%s.ma"%selection[0]), type="mayaAscii", es=True)
				print("Shader exported [shader_%s.ma]"%(selection[0]))
			
			except:
				mc.error("Impossible to export shader!")
				return
			#update the list in the textscrolllist
			#list files in the shader data base library
			content_list = os.listdir(os.path.join(mc.textField(self.project_label, query=True, text=True), "PipelineManagerData/shaderDataBase/"))
			file_list = []
			for content in content_list:
				
				if os.path.isfile(os.path.join(mc.textField(self.project_label, query=True, text=True), "PipelineManagerData/shaderDataBase/%s"%content))==True:
					#check the starting keyword in the filename
					filename = os.path.splitext(os.path.basename(content))[0].split("_")
					#print(filename)
					if filename[0] == "shader":
						file_list.append(content)
			mc.textScrollList(self.saved_shader_textscrolllist, edit=True, removeAll=True, append=file_list)

			






	def refresh_shaderlibrary_function(self,event):
		"""
		check shader list in current scene
		"""
		if self.additionnal_settings != None:
			if self.additionnal_settings["renderShaderNodeList"] != None:
				shader_list = []
				
				shader_node_list = self.additionnal_settings["renderShaderNodeList"]
				for shader_node in shader_node_list:
					try:
						shader_list+=mc.ls(type=shader_node)
					except:
						mc.warning("Impossible to get list of elements in scene\nfor this type [%s]"%shader_node)
						continue

				mc.textScrollList(self.current_shader_textscrolllist, edit=True, removeAll=True, append=sorted	(shader_list))

			#check saved shaders in pipelinemanagerdata folder
			try:
				saved_shader_list = os.listdir(os.path.join(mc.textField(self.project_label, query=True, text=True), "PipelineManagerData/shaderDataBase/"))
				if saved_shader_list != None:
					for element in saved_shader_list:
						if os.path.isfile(os.path.join(mc.textField(self.project_label, query=True, text=True), "PipelineManagerData/shaderDataBase/%s"%element))==False:
							saved_shader_list.remove(element)
						elif (element.startswith("shader_")==False) or (len(element.split("shader_"))!=2):
							saved_shader_list.remove(element)

				mc.textScrollList(self.saved_shader_textscrolllist, edit=True, removeAll=True, append=sorted	(saved_shader_list))
			except:
				mc.warning("Impossible to get saved shaders list!")
				return 


	def checking_frame_define_folder_function(self, event):
		"""
		try to define the starting folder
		project path + render folder in project path
		"""
		final_path = None	
		project_path = mc.workspace(query=True, active=True)
		if os.path.isdir(project_path)==True:
			final_path = project_path

			#print(self.additionnal_settings["renderFolderInProject"])
			if self.additionnal_settings["renderFolderInProject"] != None:
				#try to find that folder in the project
				found=False
				for r, d, f in os.walk(final_path):
					for directory in d:
						print(directory)
						if os.path.basename(directory) == self.additionnal_settings["renderFolderInProject"]:
							final_path = os.path.join(r, directory)
							print("FOUND!!!!")
							found=True
							break
					if found != False:
						break
		if found == False:
			mc.warning("Unable to find the render folder in the project!")
		#final path == starting folder


		folder=mc.fileDialog2(fm=3, startingDirectory=final_path)
		if folder == None:
			mc.error("You have to define a folder containing your batch render!")
			return
		print("Batch render folder defined successfully\n%s"%folder)

		"""
		check the first folder
		separate according to syntax settings and get first and last file!
		"""
		folder_list = os.listdir(folder[0])
		for element in folder_list:
			if os.path.splitext(element)[1] != "":
				folder_list.remove(element)
		if len(folder_list) == 0:
			mc.error("The folder doesn't contain anything!")
			return
		file_list = os.listdir(os.path.join(folder[0],folder_list[0]))
		for file in file_list:
			#check that it's a file
			if os.path.splitext(file)[0] == "":
				file_list.remove(file)

		#get the first file and the last file in the file list
		first_file=file_list[0]
		#get the snytax of the first file
		if len(self.additionnal_settings["renderFrameSyntax"]) == 0:
			mc.error("Impossible to get frame range!")
			return

		"""
		CHECKLIST FRAME NOMENCLATURE
			same split method (. _)
			same length
			same method
		"""
		syntax_result = False
		splited_syntax = None
		splited_filename = None
		spliting_method = None

		
		for syntax in self.additionnal_settings["renderFrameSyntax"]:
			f = os.path.splitext(file_list[0])[0]
			if "." in f:
				spliting_method = "."
			elif "_" in f:
				spliting_method = "_"
			else:
				mc.error("Impossible to split syntax!")
				return


			splited_syntax = syntax.split(spliting_method)
			splited_filename = f.split(spliting_method)

			if ("[content]" in splited_syntax) == False:
				mc.error("Impossible to get content in nomenclature!")
				return
			if ("[frame]" in splited_syntax)==False:
				mc.error("Impossible to get frame range in nomenclature!")
				return


			if len(splited_syntax) == len(splited_filename):
					print("SYNTAX FOUND!")
					syntax_result = True
					break
		
		if syntax_result ==False:
			mc.error("Renders are not matching with nomenclatures!")
			return

		#get first frame index
		frame_index = splited_syntax.index("[frame]")
		first_frame_content = splited_filename[splited_syntax.index("[content]")]
		first_frame = splited_filename[splited_syntax.index("[frame]")]


		file_list.pop(0)

		print("CHECKING CONTENT!")
		for file in file_list:
			#split the files according to the syntax method
			splited_f = os.path.splitext(file)[0].split(spliting_method)
			#print(splited_f, splited_filename)
			if len(splited_f) != len(splited_filename):
				continue
			else:
				frame_content = splited_f[splited_syntax.index("[content]")]
				if frame_content == first_frame_content:
					continue
				else:
					last_frame = splited_f[splited_syntax.index("[frame]")]
		if (last_frame.isdigit()==False) or (first_frame.isdigit()==False):
			mc.error("Frames are not well indicated in nomenclature!")
			return
		mc.intField(self.render_startingframe_textfield, edit=True, value=int(first_frame))
		mc.intField(self.render_endingframe_textfield, edit=True, value=int(last_frame))

		self.default_render_spliting_method = spliting_method
		self.root_render_folder = folder
		self.default_render_nomenclature = splited_syntax