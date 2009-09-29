#!/usr/bin/python
#fixed the bug with not loading when ran by root.
#need to fix password change functions for root user.
##This program was designed to assist users
##in adding, modifiying and removing usershares on a samba server which allows such access.
##It also proveds a GUI for the user to change their password in.
##Copyright (C) <2007>  <David Braker>
##    This program is free software; you can redistribute it and/or modify
##    it under the terms of the GNU General Public License as published by
##    the Free Software Foundation; either version 2 of the License, or
##    (at your option) any later version.

##    This program is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##    GNU General Public License for more details.

##    You should have received a copy of the GNU General Public License along
##    with this program; if not, write to the Free Software Foundation, Inc.,
##    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
##On Debian GNU/Linux system you can find a copy of this
##license in `/usr/share/common-licenses/GPL'.

#
#
#
###README   the command net usershare list -l    will list all the usershares and is needed when root is deleting one
### the usershare  conf files are located in /var/lib/samba/usershares/ and you can get owner information from there 
#
#
#
import pygtk
pygtk.require('2.0')
import configobj,gtk,popen2,os,time,sys,gettext
APP = 'smb-usershare'
DIR = '/usr/share/locale/'
gettext.bindtextdomain(APP, DIR)
gettext.textdomain(APP)
_ = gettext.gettext
VERSION="0.1.1"
if "-V" in sys.argv:
	print "Smb-Usershare version: ",VERSION
	sys.exit()
if "-h" in sys.argv:
	print "Usage:"
	print "\t-h \t"+_("Display this message")
	print "\t-v \t"+_("Verbose mode")
	print "\t-V \t"+_("Diplay Version information.")
	print "\t-p \t"+_("Start in Add Share mode with the path")
	print "\t\t"+_("filled in with the path provided.")
	print "\t\t"+_("Example:")
	print ""
	print "\t\t"+_("smb-usershare -p /home/user/Music")
	print ""
	sys.exit()
if "-v" in sys.argv:
	print "verbose mode"
else:
	sys.stdout=open("/dev/null", 'w')
	sys.stdin=open("/dev/null", 'r')
START_MSG=None
print os.popen("groups").readline()
if "sambashare" in os.popen("groups").readline():
	print "excellente"
elif "root" in os.popen("groups").readline():
	print "excellente"
else:
	START_MSG=_("You are not a member of the group 'sambashare'. You are not allowed to use this program. Contact your administrator and beg him to let you in.")
	print START_MSG
share_list=[]
input,output,error_out=os.popen3("net usershare list")
for line in output:
	share_list.append(line.strip())
for line in error_out:
	if "net usershare: usershares are currently disabled" in line:
		print "Usershare disabled"
		START_MSG=line+"\n"+_("Ask your administrator to set 'usershare max shares' in the 'global' section of smb.conf to a value greater than 0")
		
#		sys.exit()
class GUI(gtk.Window):
	def __init__(self):
		gtk.Window.__init__(self)
		##Main Layout part I##
		self.addsharbox=gtk.VBox()
		self.sharbox_list=gtk.VBox()
		self.sharbox=gtk.VBox()
		self.sharbox.pack_start(self.addsharbox,True,True,1)
		self.sharbox.pack_start(self.sharbox_list,True,True,1)
		##End Main Layout part I##
		##Interior share layout##
		sh_lbl=gtk.Label(_("Share Name:"))
		self.sh_entry=gtk.Entry()
		comment_lbl=gtk.Label(_("Comment:"))
		self.comment_entry=gtk.Entry()
		local_lbl=gtk.Label (_("Location: "))
		self.local_entry=gtk.Entry()
		self.local_btn=gtk.Button(stock=gtk.STOCK_OPEN)
		self.local_btn.get_children()[0].get_children()[0].get_children()[1].set_label(_("Browse"))
		self.local_btn.connect("clicked", self.folder_sel)
		self.public_sel= gtk.CheckButton(_("Open To the Public"),True)

		self.sharelist = gtk.ListStore(int,str,str,str)
		self.sharetreeview = gtk.TreeView(self.sharelist)
		
		self.sharescrolledwindow = gtk.ScrolledWindow()
		self.sharescrolledwindow.set_policy(True, True)
		self.sharescrolledwindow.add(self.sharetreeview)
		self.sharemodel = self.sharetreeview.get_selection()
		self.sharemodel.set_mode(gtk.SELECTION_SINGLE)
		self.shareR = gtk.CellRendererText()
		self.sharetreeview.insert_column_with_attributes(0, _("Shared Folders"), self.shareR, text=1)
		self.sharetreeview.insert_column_with_attributes(1, _("Comment"), self.shareR, text=2)
		self.sharetreeview.insert_column_with_attributes(2, _("Path"), self.shareR, text=3)
		self.sharetreeview.set_model(self.sharelist)
		self.sharetreeview.set_search_column(0)
		self.sharetreeview.connect("row-activated", self.share_selected)
		add_btn=gtk.Button(stock=gtk.STOCK_OK)
		add_btn.connect("clicked",self.add_share)
		reset_btn=gtk.Button(stock=gtk.STOCK_CLEAR)
		reset_btn.connect("clicked",self.share_clear)
		cancel_btn=gtk.Button(stock=gtk.STOCK_CANCEL)
		cancel_btn.connect("clicked",self.add_share_deactivate)
		add_btn2=gtk.Button(stock=gtk.STOCK_ADD)
		add_btn2.connect("clicked",self.add_share_activate)
		del_btn=gtk.Button(stock=gtk.STOCK_DELETE)
		del_btn.connect("clicked",self.del_share)
		self.mod_btn=gtk.Button(stock=gtk.STOCK_EDIT)
		self.mod_btn.connect("clicked",self.activate_share_sel)
		
		shar_bbox=gtk.HButtonBox()
		shar_bbox.pack_start(add_btn2,False,True,0)
		shar_bbox.pack_start(self.mod_btn,False,True,0)
		shar_bbox.pack_start(del_btn,False,True,0)
		
		comment_box=gtk.HBox()
		comment_box.pack_start(comment_lbl,False,False,2)
		comment_box.pack_start(self.comment_entry,False,False,23)
		
		local_box=gtk.HBox()
		local_box.pack_start(local_lbl,False,False,2)
		local_box.pack_start(self.local_entry,False,False,28)
		local_box.pack_start(self.local_btn,False,False,2)
		
		sh_box=gtk.HBox()
		sh_box.pack_start(sh_lbl,False,False,2)
		sh_box.pack_start(self.sh_entry,False,False,10)
		
		btn_box=gtk.HButtonBox()
		btn_box.pack_start(add_btn,False,True,0)
		btn_box.pack_start(cancel_btn,False,True,0)
		btn_box.pack_start(reset_btn,False,True,0)

		#~ self.user_accesslist = gtk.ListStore(int,str,str)
		#~ self.user_accesstreeview = gtk.TreeView(self.user_accesslist)
		#~ self.user_accessscrolledwindow = gtk.ScrolledWindow()
		#~ self.user_accessscrolledwindow.set_policy(True, True)
		#~ self.user_accessscrolledwindow.add(self.user_accesstreeview)
		#~ self.user_accessmodel = self.user_accesstreeview.get_selection()
		#~ self.user_accessmodel.set_mode(gtk.SELECTION_SINGLE)
		#~ self.user_accessR = gtk.CellRendererText()
		
		#~ self.user_accesstreeview.insert_column_with_attributes(0, "User", self.user_accessR, text=1)
		#~ self.user_accesstreeview.insert_column_with_attributes(1, "Access", self.user_accessR, text=2)
		user_access_ent_box=gtk.HBox()
		#~ self.user_access_entry=gtk.Entry()
		self.user_access_label=gtk.Label(_("Choose the type of access for users."))
		#~ self.user_access_ok_btn=gtk.Button(stock=gtk.STOCK_OK)
		#~ self.user_access_del_btn=gtk.Button(stock=gtk.STOCK_DELETE)
		self.user_access_cmb=gtk.combo_box_new_text()
		self.user_access_cmb.append_text("Access:")
		self.user_access_cmb.append_text("Read Only")
		self.user_access_cmb.append_text("Full Access")
		self.user_access_cmb.append_text("Deny")
		self.user_access_cmb.set_active(0)
		#~ user_access_ent_box.pack_start(self.user_access_entry,False,True,1)
		#~ user_access_ent_box.pack_start(self.user_access_entry,False,True,1)
		user_access_ent_box.pack_start(self.user_access_label,False,True,1)
		user_access_ent_box.pack_start(self.user_access_cmb,False,True,1)
		#~ user_access_ent_box.pack_start(self.user_access_ok_btn,False,True,1)
	
		self.addsharbox.pack_start(sh_box,False,False,0)
		self.addsharbox.pack_start(comment_box,False,False,0)
		self.addsharbox.pack_start(local_box,False,True,0)
		self.addsharbox.pack_start(self.public_sel,False,True,0)
		self.addsharbox.pack_start(user_access_ent_box,False,True,1)
		#~ self.addsharbox.pack_start(self.user_access_label,False,True,1)
		#~ self.addsharbox.pack_start(user_access_ent_box,False,True,0)
		#~ self.addsharbox.pack_start(self.user_accessscrolledwindow,True,True,0)
		#~ self.addsharbox.pack_start(self.user_access_del_btn,False,False,1)
		self.addsharbox.pack_end(btn_box,False,True,0)
			##right side##
		#self.sharbox_list.pack_start(self.sharetreeview,True,True,0)
		self.show_all_shares= gtk.CheckButton(_("Show shares from all users"),True)
		self.show_all_shares.connect("clicked",self.updateshare)
		if os.geteuid()==0:
			print "ROOT USER"
			self.sharbox_list.pack_start(self.show_all_shares,False,True,0)
			
		self.sharbox_list.pack_start(self.sharescrolledwindow,True,True,0)
		self.sharbox_list.pack_end(shar_bbox,False,True,0)
		##End Interior share layout##
		ch_pw_hbox=gtk.HBox()
		ch_pw_box=gtk.VBox()
		ch_pw_label=gtk.Label(_("Change password for:")+" "+os.environ.get('USER') )
		old_pw_lbl=gtk.Label(_("Enter the old password:"))
		new_pw_lbl=gtk.Label(_("Enter the new password:"))
		confirm_pw_lbl=gtk.Label(_("Confirm the new password:"))
		self.old_pw_entry=gtk.Entry()
		self.new_pw_entry=gtk.Entry()
		self.confirm_pw_entry=gtk.Entry()
		self.new_pw_entry.set_visibility(False)
		self.new_pw_entry.set_invisible_char("*") 
		self.old_pw_entry.set_visibility(False)
		self.old_pw_entry.set_invisible_char("*") 
		self.confirm_pw_entry.set_visibility(False)
		self.confirm_pw_entry.set_invisible_char("*") 
		change_btn=gtk.Button(_("Change"))
		change_btn.connect("clicked",self.ch_pw)
		ch_pw_box.pack_start(ch_pw_label,False,False,1)
		ch_pw_box.pack_start(old_pw_lbl,False,False,1)
		ch_pw_box.pack_start(self.old_pw_entry,False,False,1)
		ch_pw_box.pack_start(new_pw_lbl,False,False,1)
		ch_pw_box.pack_start(self.new_pw_entry,False,False,1)
		ch_pw_box.pack_start(confirm_pw_lbl,False,False,1)
		ch_pw_box.pack_start(self.confirm_pw_entry,False,False,1)
		ch_pw_box.pack_start(change_btn,False,False,1)
		ch_pw_hbox.pack_start(ch_pw_box,False,False)
		if os.environ.get('USER')=="root":
			self.old_pw_entry.set_sensitive(False)
		else:
			self.old_pw_entry.set_sensitive(True)
		class image_label(gtk.HBox):
			def create(self,image,label):
				IMAGE=gtk.Image()
				IMAGE.set_from_icon_name(image,4)
				LABEL=gtk.Label(label)
				self.pack_start(IMAGE)
				self.pack_start(LABEL)
				self.show_all()
		share_label=image_label()
		share_label.create("gnome-fs-smb",_("User Shared Folders"))
		ch_pw_tab_label=image_label()
		ch_pw_tab_label.create("dialog-password",_("Change Password"))
		system_label=image_label()
		#The previous lines are to set an image plus text for the "shares" label on the notebook.
		#to enable it uncomment them and change the set_tab_label_text for that tab to set_tab_label
		##Main Layout part II##
		self.notebook=gtk.Notebook()
		self.notebook.set_show_border(False)
		self.notebook.insert_page(self.sharbox,tab_label=None,position=0)
		
		#self.notebook.set_tab_label_text(self.sharbox,"Shared Folder Settings")
		self.notebook.set_tab_label(self.sharbox,share_label)
		self.notebook.insert_page(ch_pw_hbox,tab_label=None,position=1)
		self.notebook.set_tab_label(ch_pw_hbox,ch_pw_tab_label)
		
		self.notebook.set_tab_pos(gtk.POS_LEFT)
		#self.notebook.connect("switch-page", self.tab_clicked)
		hsep=gtk.HSeparator()
		quitbtn=gtk.Button(stock="gtk-quit")
		
		#quitbtn.get_children()[0].get_children()[0].get_children()[1].set_label("EXIT NOW")
		about=gtk.Button(stock=gtk.STOCK_ABOUT)#"About")
		about.connect("clicked",self.abtfunc)
		quitbtn.connect("clicked",self.delete_event)
		bbox=gtk.HButtonBox()
		bbox.pack_start(about,False,True,0)
		bbox.pack_start(quitbtn,False,True,0)
		vbox=gtk.VBox()
		vbox.pack_start(self.notebook,True,True,0)
		vbox.pack_start(hsep,False,False,10)
		vbox.pack_start(bbox,False,True,0)
		##End Main Layout part II##
		self.set_title("Smb-Usershare")
		self.connect("delete_event", self.delete_event)
		self.add(vbox)
		self.show_all()
		self.pw_entry2=gtk.Entry()
		self.pw_entry3=gtk.Entry()
		self.uname_entry2=gtk.Entry()
		self.addsharbox.hide()
		self.set_size_request(390,300)
	def abtfunc(self,widget):
		global VERSION
		x=gtk.AboutDialog()
		x.set_version(VERSION)
		x.set_name("Smb-Usershare")
		y=["David Braker (LinuxNIT)\nContact: linuxnit@elivecd.org"]
		x.set_authors(y)
		if os.access("/usr/share/pixmaps/smb-browser.png",0)==True:
			image=gtk.gdk.pixbuf_new_from_file_at_size("/usr/share/pixmaps/smb-browser.png",60,60)
		else:
			image=None
		x.set_logo(image)
		def close(w, res):
			if res == gtk.RESPONSE_CANCEL:
				w.hide()
		x.connect("response", close)
		x.set_wrap_license(True)
		x.set_license(_("This program was designed to assist users in adding, modifiying and removing usershares on a samba server which allows such access. It also proveds a GUI for the user to change their password in. Copyright (C) <2007>  <David Brakers> This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version. This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details. You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA. On a Debian GNU/Linux system you can find a copy of this license in `/usr/share/common-licenses/'."))
		x.set_comments(_("This program was designed to assist users in adding, modifiying and removing usershares on a samba server which allows such access. It also proveds a GUI for the user to change their password in."))
		x.show()
	def activate_share_sel(self,widget):
		self.share_selected(None,None,None)
	def add_share_activate(self,widget):
		print "add share activated"
		print self.sh_entry.get_text()
		global ORIGINAL_SHARE
		ORIGINAL_SHARE=self.sh_entry.get_text()
		if ORIGINAL_SHARE=="":
			self.user_access_cmb.set_active(0)
		self.sharbox_list.hide()
		self.addsharbox.show()
	def add_share_deactivate(self,widget):
		self.sharbox_list.show()
		self.addsharbox.hide()
		self.share_clear(None)

	def add_share(self,widget):
		state=[]
		if self.show_all_shares.get_active()==True:
			print "ACTIVE"
			#share_list=os.popen("net usershare list -l").readlines()
			COMMAND="net usershare -l"
		else:
			print "FALSE"
			#share_list=os.popen("net usershare list").readlines()
			COMMAND="net usershare "

		global ORIGINAL_SHARE
		print ORIGINAL_SHARE,"this is the original share"
		sharename=self.sh_entry.get_text().strip()
		if sharename.strip()=="":
			return self.msgbox(_("Please enter a sharename."))
		elif self.local_entry.get_text().strip()=="":
			return self.msgbox(_("Please enter a share path."))
		path=self.local_entry.get_text()
		comment=self.comment_entry.get_text()
		if self.public_sel.get_active() == True:
			public="yes"
		elif self.public_sel.get_active() == False:
			public="no"
		user_acl="Everyone:r"
		model = self.user_access_cmb.get_model()
		index = self.user_access_cmb.get_active()
		access_type=model[index][0]
		if access_type=="Access:" and ORIGINAL_SHARE != "":
			#in this case the user is modifying an existing share and
			#the user has predefined usershare_acl settings which we dont 
			#want to change unless they do
			#the following will obtain the current usershare_acl setting for sharename
			info=os.popen(COMMAND+" info "+sharename)
			for line in info:
				if line.startswith("usershare_acl"):
					user_acl=line.split("=")[1].strip().lower().strip(",")
		elif access_type!="Access:" and ORIGINAL_SHARE != "":
			#the  user is modifying a share
			#the user has chosen a access type so either they want to over-ride the 
			#current usershare_acl settings or this the original usershare_acl contained
			#a setting for "Everyone"
		#elif ORIGINAL_SHARE == "":
			if access_type =="Read Only":
				user_acl="Everyone:r"
			elif access_type =="Full Access":
				user_acl="Everyone:f"
			elif access_type =="Deny":
				user_acl="Everyone:d"
			elif access_type =="Access:":
				user_acl="Everyone:r"
		elif ORIGINAL_SHARE =="":
			#in this case the user is creating a new share
			if access_type =="Read Only":
				user_acl="Everyone:r"
			elif access_type =="Full Access":
				user_acl="Everyone:f"
			elif access_type =="Deny":
				user_acl="Everyone:d"
			elif access_type =="Access:":
				user_acl="Everyone:r"
		if "Everyone" not in user_acl and public == "yes":
			return self.msgbox(_("If you want to allow guest access, you must have a usershare_acl setting for \"Everyone.\" To add one, select an access mode from the drop down menu. This will remove the current usershare_acl settings for the share since a setting for 'Everyone' will over-ride any other settings."))
		command ="net usershare add \""+sharename+"\" \""+path+"\" \""+comment+"\" \""+user_acl+"\" guest_ok="+public
		print command
		input,out1,out2=os.popen3(command)
		output=out2.readlines()
		if output==[]:
			print "share added"
			self.msgbox(_("Share Added"))
		else:
			print "else"
			msg=""
			out2.read
			for x in output:
				print x
				msg=msg+x
#				print msg
			for x in out1.readlines():
				print x
				msg=msg+x
#				print msg
			self.msgbox(msg)
		self.share_clear(None)
		self.add_share_deactivate(None)
		return gui.updateshare(None)
	def ch_pw(self,widget):
		old_pw=self.old_pw_entry.get_text()
		new_pw=self.new_pw_entry.get_text()
		confirm_pw=self.confirm_pw_entry.get_text()
		if confirm_pw.strip()==new_pw.strip():
			output,input=popen2.popen4("smbpasswd -s ")
			if os.environ.get('USER')!="root":
				input.write(old_pw+"\n")
			input.write(new_pw+"\n")
			input.write(confirm_pw+"\n")
			status=input.close()
			result=output.read()
			if status is None:
				output.close()
				self.msgbox(result)
			else:
				output.close()
				self.msgbox("printing",status,result)
		else:
			self.msgbox(_("The passwords dont match."))

	def delete_event( widget, event=None, data=None):
		gtk.main_quit()
		return False
	def del_share(self,widget):
		s = self.sharetreeview.get_selection()
		(ls, iter) = s.get_selected()	
		if iter is None:
			print "nothing selected"
		else:
			sharename=ls.get_value(iter, 1)
		if sharename !="":
			input,out1,out2=os.popen3("net usershare delete "+sharename)
			output=out2.readlines()
			if output==[]:
				print "share deleted"
				self.msgbox(_("Share Deleted"))
			else:
				print "else"
				msg=""
				out2.read
				for x in output:
					print x
					msg=msg+x
	#				print msg
				for x in out1.readlines():
					print x
					msg=msg+x
	#				print msg
				self.msgbox(msg)
			self.share_clear("worthless data")
		gui.updateshare(None)
	def folder_sel(self,widget):	
		filew = gtk.FileChooserDialog(title=_("Choose a folder"),action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
			buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
		response=filew.run()
		if response ==gtk.RESPONSE_OK:
			self.local_entry.set_text(filew.get_filename())
		filew.destroy()
	
	def msgbox(self,MSG):
		popup = gtk.MessageDialog(parent=None, flags=gtk.MESSAGE_WARNING, buttons=gtk.BUTTONS_OK, message_format=MSG)
		popup.set_position(gtk.WIN_POS_CENTER_ALWAYS)
		popup.show_all()
		popup.run()
		popup.destroy()
		return True

	def share_selected(self,x,y,widget):
		print "SHARE SELECTED FUNC"
		if self.show_all_shares.get_active()==True:
			return
		s = self.sharetreeview.get_selection()
		(ls, iter) = s.get_selected()	
		if iter is None:
			print "nothing selected"
			return
		else:
			sharename=ls.get_value(iter, 1)
		print sharename
		self.sh_entry.set_text(sharename)
		config=configobj.ConfigObj(os.popen("net usershare  info "+sharename))
		self.local_entry.set_text(config[sharename]["path"])
		self.comment_entry.set_text(config[sharename]["comment"])
		if config[sharename]["guest_ok"] == "y":
			self.public_sel.set_active(True)#.append("Yes")
		elif config[sharename]["guest_ok"] == "n":	
			self.public_sel.set_active(False)#.append("No")
		#~ self.list_user_access(None)
	#~ def list_user_access(self,widget):
		#~ sharename=self.sh_entry.get_text()
		#~ config=configobj.ConfigObj(os.popen("net usershare info "+sharename))
		#~ z=0
		#~ self.user_accesslist.clear()
		#self.user_access_cmb.set_active(1)
		everyone_present=False
		for perm in config[sharename]["usershare_acl"]:
			print perm,"######"
			if "Everyone" in perm:
				everyone_present=True
				print perm.split(":")[1],"########################"
			#~ print perm
			#~ name=perm.split(":")[0]
				if perm.split(":")[1].strip() == "F":
					self.user_access_cmb.set_active(2)
					access="Full"
					#access.append("Full")
				elif perm.split(":")[1].strip() == "R":
					self.user_access_cmb.set_active(1)
					access="Read Only"
				elif perm.split(":")[1].strip() == "D":
					self.user_access_cmb.set_active(3)
					access="Denied"
#				print access
				#~ if "\\" in name:
					#~ name=name.split("\\")[1]
			#~ iter = self.user_accesslist.append( [z,name,access])#comment[z],readonly[z],public[z],path[z]] )
			#~ z=z+1
		if everyone_present==False:
			self.user_access_cmb.set_active(0)
		#~ if "public" in config[sharename]:
			#~ if config[sharename]["public"].lower() in ["true","yes"]:
				#~ self.pub_sel.set_active(True)
			#~ else:
				#~ self.pub_sel.set_active(False)
		self.add_share_activate(None)
	
	def share_clear(self,widget):
		self.sh_entry.set_text("")
		self.local_entry.set_text("")
		self.comment_entry.set_text("")
		self.public_sel.set_active(False)
		self.user_access_cmb.set_active(0)
	def updateshare(self,widget):
		self.sharelist.clear()
		z=0
		shares=[]
		comments=[]
		permissions=[]
		public=[]
		path=[]
		if self.show_all_shares.get_active()==True:
			print "ACTIVE"
			#share_list=os.popen("net usershare list -l").readlines()
			COMMAND="net usershare -l"
			self.mod_btn.set_sensitive(False)
		else:
			print "FALSE"
			#share_list=os.popen("net usershare list").readlines()
			COMMAND="net usershare "
			self.mod_btn.set_sensitive(True)
		share_list=os.popen(COMMAND+" list").readlines()
		print share_list
		print "FOR LOOP NEXT"
		for share in share_list:
			print share
			share=share.strip()
			info_conf=configobj.ConfigObj(os.popen(COMMAND+" info "+share))
			comments.append(info_conf[share]["comment"])
			path.append(info_conf[share]["path"])
			iter = self.sharelist.append( [z,share,comments[z],path[z]])#comment[z],readonly[z],public[z],path[z]] )
			z=z+1


gui=GUI()
gui.updateshare(None)
gui.share_clear(None)
if START_MSG!=None:
	gui.msgbox(START_MSG)
	sys.exit()
if "-p" in sys.argv:
	ORIGINAL_SHARE=""
	gui.sharbox_list.hide()
	gui.addsharbox.show()
	gui.local_entry.set_text(sys.argv[sys.argv.index("-p")+1])
	gui.sh_entry.set_text(sys.argv[sys.argv.index("-p")+1].rsplit("/",1)[1])

gtk.main()
