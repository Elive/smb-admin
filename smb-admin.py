#!/usr/bin/python

#fixed bug in createing a newconfig when one is not present.
#fixed bug in setting the default value for usershare max shares
##This program was designed to assist users
##in managing samba settings, shares and users.
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
##license in `/usr/share/common-licenses/'.
##On Arch Linux system you can find a copy of this
##license in '/usr/share/licenses/common/'.
import pygtk
pygtk.require('2.0')
#import popen2
import configobj,gtk,os,time,sys,threading,gettext
import subprocess as subp
APP = 'smb-admin'
DIR = '/usr/share/locale/'
gettext.bindtextdomain(APP, DIR)
gettext.textdomain(APP)
_ = gettext.gettext
VERSION="1.04.7"
if len(sys.argv)>1:
	ARG=sys.argv[1]
	if ARG=="-v":
		print _("verbose mode")
	if ARG=="-V":
		print _("Smb-Admin version: "),VERSION
		sys.exit()
else:
	sys.stdout=open("/dev/null", 'w')
	sys.stdin=open("/dev/null", 'r')
if os.access("/etc/debian_version",0)==True:
	print "this is a debian system"
	if os.access("/etc/init.d/samba",os.X_OK):
		RESTART_CMD="/etc/init.d/samba restart"
	elif os.access("/etc/init.d/smb",os.X_OK):
		RESTART_CMD="/etc/init.d/smb restart"
elif os.access("/etc/arch-release",0)==True:
	print "this is an arch linux system"
	RESTART_CMD="/etc/rc.d/samba restart"
if os.getuid()!=0:
	os.system("gksu smb-admin")
	sys.exit()
outfile=open("/tmp/tmp.conf","w")
def create_conf():
	config=configobj.ConfigObj()
	config["global"]={}
	config["global"]["os level"]="20"
	config["global"]["workgroup"]="Workgroup"
	config["global"]["server string"]="%h server"
	config["global"]["passdb backend"]="tdbsam"
	config["global"]["local master"]="yes"
	config["global"]["preferred master"]="no"
	config["global"]["wins support"]="no"
	config["global"]["load printers"]="yes"
	config["homes"]={}
	config["homes"]["browseable"]="no"
	config["homes"]["writeable"]="yes"
	config["homes"]["available"]="yes"
	config["homes"]["public"]="no"
	config["homes"]["follow symlinks"]="yes"
	config["homes"]["comment"]="Shared user home directories"
	return config
if os.access("/etc/samba/smb.conf",0)==True:
	file=open("/etc/samba/smb.conf","r")
	for line in file:
		line=line.lstrip()
		if line.startswith(";"):
			line=line.lstrip(";")
			line="###"+line
		if line.startswith("#"):
			line=" \t"+line
		outfile.write(line)
	outfile.close()
	try:
		config=configobj.ConfigObj("/tmp/tmp.conf")
	except configobj.ConfigObjError, ERROR_OUTPUT:
		print ERROR_OUTPUT
		config = ERROR_OUTPUT.config
		
else:
	print "no smb.conf in /etc/samba/ creating a blank one"
	config=create_conf()
	config.filename="/etc/samba/smb.conf"
	config.write()
for key in config.keys():
	for subkey in config[key].keys():
		config[key].rename(subkey,subkey.lower())
	config.rename(key,key.lower())

orig_config=configobj.ConfigObj(config)
compare_conf=configobj.ConfigObj(config)
for x in  config.keys():
	if "guest ok" in config[x]:
		public_val=config[x]["guest ok"]
		config[x]["public"]=public_val
		del config[x]["guest ok"]
	if "browsable" in config[x]:
		bro_val=config[x]["browsable"]
		config[x]["browseable"]=bro_val
		del config[x]["browsable"]
	if "write ok" in config[x]:
		write_val=config[x]["write ok"]
		config[x]["writeable"]=write_val
		del config[x]["write ok"]
	if "read only" in config[x]:
		read_val=config[x]["read only"].lower()
		if read_val in ["yes","true"]:
			read_val = "no"
		elif read_val in ["no","false"]:
			read_val= "yes"
		config[x]["writeable"]=read_val
		del config[x]["read only"]

class GUI(gtk.Window):
	def __init__(self):
		gtk.Window.__init__(self)
		##Main Layout part I##
		global_box=gtk.VBox()
		self.addsharbox=gtk.VBox()
		self.sharbox_list=gtk.VBox()
		self.sharbox=gtk.VBox()
		self.sharbox.pack_start(self.addsharbox,True,True,1)
		self.sharbox.pack_start(self.sharbox_list,True,True,1)
		##End Main Layout part I##
		##Interior general layout##
		wg_box=gtk.HBox()
		wg_lbl=gtk.Label(_("Workgroup"))
		self.wg_entry=gtk.Entry()
		wg_box.pack_start(wg_lbl,False,True,2)
		wg_box.pack_start(self.wg_entry,False,True,73)
		
		serverstr_box=gtk.HBox()
		serverstr_lbl=gtk.Label(_("Sever String"))
		self.serverstr_entry=gtk.Entry()
		serverstr_box.pack_start(serverstr_lbl,False,True,2)
		serverstr_box.pack_start(self.serverstr_entry,False,True,65)
		
		nb_name_box=gtk.HBox()
		nb_name_lbl=gtk.Label(_("NetBios Name"))
		self.nb_name_entry=gtk.Entry()
		nb_name_box.pack_start(nb_name_lbl,False,True,2)
		nb_name_box.pack_start(self.nb_name_entry,False,True,51)
		
		
		self.prefmb_sel=gtk.CheckButton(_("Preferred Master Browser(one per network)"), False)
		self.prefmb_sel.connect("clicked", self.prefmb_func)
		self.localmb_sel= gtk.CheckButton(_("Local Master Browser"),True)
		self.localmb_sel.connect("clicked", self.localmb_func)
		
		oslvl_box=gtk.HBox()
		oslvl_lbl=gtk.Label(_("OS Level"))
		self.oslvl_entry=gtk.Entry()
		self.oslvl_entry.set_width_chars (8)
		oslvl_box.pack_start(oslvl_lbl,False,True,2)
		oslvl_box.pack_start(self.oslvl_entry,False,True,90)
	
		self.winserv_sel=gtk.RadioButton(None,_("Do not act as WINS server"))
		self.winserv_sel2=gtk.RadioButton(self.winserv_sel,_("Act as WINS server"))
		self.winserv_sel3=gtk.RadioButton(self.winserv_sel,_("Use WINS server"))
		self.winserv_entry=gtk.Entry()
		winserv_box=gtk.HBox()
		winserv_box.pack_start(self.winserv_sel3,False,True,2)
		winserv_box.pack_start(self.winserv_entry,False,True,14)
		
		
		self.winserv_sel.connect('clicked', self.winserv_func,"no")
		self.winserv_sel2.connect('clicked', self.winserv_func,"yes")
		self.winserv_sel3.connect('clicked', self.winserv_func,"server")
		
		self.usershare_allow_guest=gtk.CheckButton(_("Allow guests on usershares"))
		self.usershare_allow_guest.set_tooltip_text(_("This will allow the users who create shares to decide if guests can access the shares or not. If this is not set then no guests can access the shares."))
		self.usershare_max_shares_lbl=gtk.Label(_("Maximum number of usershares"))
		self.usershare_max_shares_entry=gtk.Entry()
		self.usershare_max_shares_entry.set_tooltip_text(_("To disable usershares, set the max number of usershares to 0"))
		self.usershare_max_shares_entry.set_width_chars (8)
		self.usershare_max_shares_hbox=gtk.HBox()
		self.usershare_max_shares_hbox.pack_start(self.usershare_max_shares_lbl,False,True,2)
		self.usershare_max_shares_hbox.pack_start(self.usershare_max_shares_entry,False,True,32)
		self.usershare_owner_only=gtk.CheckButton(_("Owners can only share their directories"))
		self.usershare_owner_only.set_tooltip_text(_("If set, then only the directories owned by the sharing user can be shared."))
		usershare_about_lbl=gtk.Label(_("Usershares are shares that the users can create, modify, and delete without being an administrator. They must be a member of the sambashare group. To disable them, set the max number of usershares to 0."))
		usershare_about_lbl.set_line_wrap(True)
		self.homes_sel= gtk.CheckButton(_("Share Home Directories"),True)
		self.homes_sel.connect("clicked", self.homes_toggle)
		
		restorebtn=gtk.Button(stock=gtk.STOCK_REVERT_TO_SAVED)#"Restore Config"
		restorebtn.get_children()[0].get_children()[0].get_children()[1].set_label(_("Restore Config"))
		restorebtn.connect("clicked",self.restore_conf)
		restorebtn.set_tooltip_text(_("This restores the configuration to what it was when the program started. Changes to the users and passwords will not be restored."))
		newbtn=gtk.Button(stock=gtk.STOCK_NEW)
		newbtn.connect("clicked",self.create_new_conf)
		newbtn.get_children()[0].get_children()[0].get_children()[1].set_label(_("New Configuration"))
		
		configbbox=gtk.HButtonBox()
		configbbox.pack_start(newbtn,False,True,1)
		configbbox.pack_start(restorebtn,False,True,1)
		
		global_box.pack_start(wg_box,False,True,1)
		global_box.pack_start(serverstr_box,False,True,1)
		global_box.pack_start(nb_name_box,False,True,1)
		global_box.pack_start(self.prefmb_sel,False,True,1)
		global_box.pack_start(self.localmb_sel,False,True,1)
		global_box.pack_start(oslvl_box,False,True,1)
		global_box.pack_start(self.winserv_sel,False,True,1)
		global_box.pack_start(self.winserv_sel2,False,True,1)
		global_box.pack_start(winserv_box,False,True,1)
		global_box.pack_start(self.usershare_allow_guest,False,True,1)
		global_box.pack_start(self.usershare_max_shares_hbox,False,True,1)
		global_box.pack_start(self.usershare_owner_only,False,True,1)
		global_box.pack_start(usershare_about_lbl,False,True,1)
		global_box.pack_end(configbbox,False,True,1)
		
		##End Interior general layout##
		##Interior share layout##
		sh_lbl=gtk.Label(_("Share Name:"))
		self.sh_entry=gtk.Entry()
		comment_lbl=gtk.Label(_("Comment:"))
		self.comment_entry=gtk.Entry()
		local_lbl=gtk.Label       (_("Location: "))
		self.local_entry=gtk.Entry()
		self.local_btn=gtk.Button(stock=gtk.STOCK_OPEN)
		self.local_btn.get_children()[0].get_children()[0].get_children()[1].set_label(_("Browse"))
		self.local_btn.connect("clicked", self.folder_sel)
		self.browseable_sel= gtk.CheckButton(_("Visible on clients"),True)
		self.write_sel= gtk.CheckButton(_("Writeable"),True)
		self.avail_sel= gtk.CheckButton(_("Enabled"),True)
		self.follow_sel=gtk.CheckButton(_("Follow symlinks"),False)
		self.pub_sel= gtk.CheckButton(_("Open to the Public"),False)
		self.pub_sel.connect("clicked",self.public_share)
		valuser_lbl=gtk.Label(_("Valid Users (optional)"))
		self.share_info=gtk.Label("")
		self.valuser_entry=gtk.Entry()
		self.valuser_entry.set_tooltip_text(_("Separate usernames with a comma"))
		
		self.sharelist = gtk.ListStore(int,str,str,str,str,str,str,str)
		self.sharetreeview = gtk.TreeView(self.sharelist)
		
		self.sharescrolledwindow = gtk.ScrolledWindow()
		self.sharescrolledwindow.set_policy(True, True)
		
		self.psharelist = gtk.ListStore(int,str,str,str,str,str)
		self.psharetreeview = gtk.TreeView(self.psharelist)
		
		scroll_box=gtk.VBox()
		self.sep_lbl=gtk.Label(_("CUPS Printers Shared by SAMBA"))
		scroll_box.pack_start(self.sharetreeview,True,True)
		self.sharescrolledwindow.add_with_viewport(scroll_box)

		self.psharemodel = self.psharetreeview.get_selection()
		self.psharemodel.set_mode(gtk.SELECTION_SINGLE)
		self.pshareR = gtk.CellRendererText()
		self.psharetreeview.insert_column_with_attributes(0, _("Printer Name"), self.pshareR, text=1)
		self.psharetreeview.insert_column_with_attributes(1, _("Comment"), self.pshareR, text=2)
		self.psharetreeview.insert_column_with_attributes(2, _("Visible"), self.pshareR, text=3)
		self.psharetreeview.insert_column_with_attributes(3, _("Enabled"), self.pshareR, text=4)
		self.psharetreeview.insert_column_with_attributes(4, _("Public"), self.pshareR, text=5)
		self.psharetreeview.set_model(self.psharelist)
		self.psharetreeview.set_search_column(0)
		self.psharetreeview.connect("row-activated", self.mod_printer)

		self.sharemodel = self.sharetreeview.get_selection()
		self.sharemodel.set_mode(gtk.SELECTION_SINGLE)
		self.shareR = gtk.CellRendererText()
		self.sharetreeview.insert_column_with_attributes(0, _("Shared Folders"), self.shareR, text=1)
		self.sharetreeview.insert_column_with_attributes(1, _("Comment"), self.shareR, text=2)
		self.sharetreeview.insert_column_with_attributes(2, _("Visible"), self.shareR, text=3)
		self.sharetreeview.insert_column_with_attributes(3, _("Enabled"), self.shareR, text=4)
		self.sharetreeview.insert_column_with_attributes(4, _("Writeable"), self.shareR, text=5)
		self.sharetreeview.insert_column_with_attributes(5, _("Public"), self.shareR, text=6)
		self.sharetreeview.insert_column_with_attributes(6, _("Path"), self.shareR, text=7)
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
		mod_btn=gtk.Button(stock=gtk.STOCK_EDIT)
		mod_btn.connect("clicked",self.activate_share_sel)

		self.prntbtn=gtk.Button(_("Add to Shared Printers"))
		self.prntbtn.connect("clicked",self.toggle_printer)
		self.prntsharelist = gtk.ListStore(int,str,str)#,str)
		self.prntsharetreeview = gtk.TreeView(self.prntsharelist)
		self.prnt_scw = gtk.ScrolledWindow()
		self.prnt_scw.set_policy(True, True)
		self.prnt_scw.add(self.prntsharetreeview)
		self.prntsharemodel = self.prntsharetreeview.get_selection()
		self.prntsharemodel.set_mode(gtk.SELECTION_SINGLE)
		self.prntshareR = gtk.CellRendererText()
		self.prntsharetreeview.insert_column_with_attributes(0, _("System Printers"), self.shareR, text=1)
		self.prntsharetreeview.insert_column_with_attributes(1, _("Shared by Samba"), self.shareR, text=2)
		#self.prntsharetreeview.insert_column_with_attributes(2, "Shared by CUPS", self.shareR, text=3)

		shar_bbox=gtk.HButtonBox()
		shar_bbox.pack_start(add_btn2,False,True,0)
		shar_bbox.pack_start(mod_btn,False,True,0)
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
		
		valuser_box=gtk.HBox()
		valuser_box.pack_start(valuser_lbl,False,True,0)
		valuser_box.pack_start(self.valuser_entry,False,True,0)
		
		self.addsharbox.pack_start(sh_box,False,False,0)
		self.addsharbox.pack_start(comment_box,False,False,0)
		self.addsharbox.pack_start(local_box,False,True,0)
		self.addsharbox.pack_start(self.browseable_sel,False,True,0)
		self.addsharbox.pack_start(self.write_sel,False,True,0)
		self.addsharbox.pack_start(self.avail_sel,False,True,0)
		self.addsharbox.pack_start(self.follow_sel,False,True,0)
		self.addsharbox.pack_start(self.pub_sel,False,True,0)
		self.addsharbox.pack_start(valuser_box,False,False,0)
		self.addsharbox.pack_start(self.share_info,False,False,0)
		self.addsharbox.pack_end(btn_box,False,True,0)
			##right side##
		#self.sharbox_list.pack_start(self.sharetreeview,True,True,0)
		self.sharbox_list.pack_start(self.homes_sel,False,True,1)
		self.sharbox_list.pack_start(self.sharescrolledwindow,True,True,0)
		self.sharbox_list.pack_end(shar_bbox,False,True,0)
		##End Interior share layout##
		##Users Interior layout##
		self.show_allusers=gtk.CheckButton(_("Show Users With Unset Passwords"),True)
		self.show_allusers.set_tooltip_text(_("Users with unset passwords can NOT log into the server"))
		self.show_allusers.connect("clicked", udu_start)
		#self.show_allusers.connect("clicked", self.updateusers)
		self.userlist = gtk.ListStore(int,str,str,str)
		self.usertreeview = gtk.TreeView(self.userlist)
		self.usermodel = self.usertreeview.get_selection()
		self.usermodel.set_mode(gtk.SELECTION_SINGLE)
		self.userR = gtk.CellRendererText()
		self.usertreeview.insert_column_with_attributes(0, _("Current Samba Users"), self.userR, text=1)
		self.usertreeview.insert_column_with_attributes(1, _("Status"), self.userR, text=2)
		self.usertreeview.insert_column_with_attributes(2, _("Password Set"), self.userR, text=3)
		self.usertreeview.set_model(self.userlist)
		self.usertreeview.set_search_column(0)
		self.userscrolledwindow= gtk.ScrolledWindow()
		self.userscrolledwindow.add(self.usertreeview)
		self.userscrolledwindow.set_policy(True, True)
		
		usermod_btn=gtk.Button(_("Change password"))
		usertog_btn=gtk.Button(_("Toggle Status"))
		useradd_btn=gtk.Button(stock=gtk.STOCK_ADD)
		userdel_btn=gtk.Button(stock=gtk.STOCK_DELETE)
		useradd_btn.connect("clicked",self.user_func,"add")
		userdel_btn.connect("clicked",self.user_func,"del")
		usermod_btn.connect("clicked",self.user_func,"changepw")
		usertog_btn.connect("clicked",self.user_func,"toggle")
		
		users_bbox=gtk.HButtonBox()
		users_bbox.pack_start(useradd_btn,False,True,0)
		users_bbox.pack_start(userdel_btn,False,True,0)
		users_bbox.pack_start(usermod_btn,False,True,0)
		users_bbox.pack_start(usertog_btn,False,True,0)
		self.users_box2=gtk.VBox()
		self.users_box2.pack_start(self.show_allusers,False,False,0)
		self.users_box2.pack_start(self.userscrolledwindow,True,True,0)
		#self.users_box2.pack_start(self.usertreeview,True,True,0)
		self.users_box2.pack_end(users_bbox,False,True,0)
		
		##End Users Interior layout##
		
		##print section
		prnt_lbl=gtk.Label(_("Sharing CUPS printers with samba"))
		self.shall_prnt= gtk.CheckButton(_("Automatically share all printers."),True)
		self.shall_prnt.connect("clicked", self.set_prnt)
		##Print box
		self.print_box=gtk.VBox(False,False)
		pmod_btn=gtk.Button(stock=gtk.STOCK_EDIT)
		pmod_btn.connect("clicked",self.activate_print_sel)
		premove_btn=gtk.Button(stock=gtk.STOCK_REMOVE)
		premove_btn.connect("clicked",self.remove_printer)
		self.print_hbbox=gtk.HButtonBox()
		self.print_hbbox.pack_start(pmod_btn)
		self.print_hbbox.pack_start(premove_btn)
		self.print_box.pack_start(prnt_lbl,False,True,0)
		self.print_box.pack_start(self.shall_prnt,False,True,0)
		self.print_box.pack_start(self.prnt_scw,True,True,0)
		self.print_box.pack_start(self.prntbtn,False,False,0)
		self.print_box.pack_start(self.sep_lbl,False,False)
		self.print_box.pack_start(self.psharetreeview,True,True)
		self.print_box.pack_start(self.print_hbbox,False,False)
		##end print box
		class image_label(gtk.HBox):
			def create(self,image,label):
				IMAGE=gtk.Image()
				IMAGE.set_from_icon_name(image,4)
				LABEL=gtk.Label(label)
				self.pack_start(IMAGE)
				self.pack_start(LABEL)
				self.show_all()
		share_label=image_label()
		share_label.create("gnome-fs-smb",_("Shared Folders"))
		system_label=image_label()
		system_label.create("preferences-system",_("Server Settings"))
		printers_label=image_label()
		printers_label.create("printer",_("Sharing CUPS Printers"))
		#The previous lines are to set an image plus text for the "shares" label on the notebook.
		#to enable it uncomment them and change the set_tab_label_text for that tab to set_tab_label
		##Main Layout part II##
		self.notebook=gtk.Notebook()
		self.notebook.set_show_border(False)
		self.notebook.insert_page(self.sharbox,tab_label=None,position=0)
		#self.notebook.set_tab_label_text(self.sharbox,"Shared Folder Settings")
		self.notebook.set_tab_label(self.sharbox,share_label)
		self.notebook.insert_page(global_box,tab_label=None,position=1)
		#self.notebook.set_tab_label_text(global_box,"General Server Settings")
		self.notebook.set_tab_label(global_box,system_label)
		self.notebook.insert_page(self.users_box2,tab_label=None,position=2)
		self.notebook.set_tab_label_text(self.users_box2,"SAMBA Users")
		self.notebook.insert_page(self.print_box,tab_label=None,position=3)
		self.notebook.set_tab_label_text(self.print_box,_("Sharing CUPS Printers"))
		self.notebook.set_tab_label(self.print_box,printers_label)
		
		self.notebook.set_tab_pos(gtk.POS_LEFT)
		self.notebook.connect("switch-page", self.tab_clicked)
		hsep=gtk.HSeparator()
		quitbtn=gtk.Button(stock="gtk-quit")
		
		#quitbtn.get_children()[0].get_children()[0].get_children()[1].set_label("EXIT NOW")
		savebtn=gtk.Button(stock="gtk-save")
		savebtn.get_children()[0].get_children()[0].get_children()[1].set_label(_("Save configuration"))
		savebtn.connect("clicked",self.save_config)
		restrtbtn=gtk.Button(stock="gtk-refresh")
		restrtbtn.get_children()[0].get_children()[0].get_children()[1].set_label(_("Restart Server"))
		restrtbtn.connect("clicked",self.restart_server)
		about=gtk.Button(stock=gtk.STOCK_ABOUT)#"About")
		about.connect("clicked",self.abtfunc)
		quitbtn.connect("clicked",self.delete_event)
		bbox=gtk.HButtonBox()
		bbox.pack_start(savebtn,False,True,0)
		bbox.pack_start(restrtbtn,False,True,0)
		bbox.pack_start(about,False,True,0)
		bbox.pack_start(quitbtn,False,True,0)
		vbox=gtk.VBox()
		vbox.pack_start(self.notebook,True,True,0)
		vbox.pack_start(hsep,False,False,10)
		vbox.pack_start(bbox,False,True,0)
		##End Main Layout part II##
		self.set_title(_("Smb-Admin"))
		self.connect("delete_event", self.delete_event)
		self.add(vbox)
		self.show_all()
		self.pw_entry2=gtk.Entry()
		self.pw_entry3=gtk.Entry()
		self.uname_entry2=gtk.Entry()
		self.unpw2=gtk.Window()
		self.addsharbox.hide()
	def create_new_conf(self,widget):
		global config
		config=create_conf()
		gui.updateshare()
		gui.read_conf()
	def check_guest(self,widget):
		print "Clicked"
	def set_prnt(self,widget):
		print widget.get_label()
		print "#####################################\n##############################"
		if self.shall_prnt.get_active()==True:
			config["global"]["load printers"]="yes"
			if "printers" not in config.sections:
				config["printers"]={}
			config["printers"]["path"]="/var/spool/samba"
			config["printers"]["printable"]="yes"
			config["printers"]["comment"]=_("All Printers")
			self.prnt_scw.set_sensitive(False)
			self.prntbtn.set_sensitive(False)
			self.updateshare()
		elif self.shall_prnt.get_active()==False:
			if "printers" in config.keys():
				del config["printers"]
			config["global"]["load printers"]="no"
			self.prnt_scw.set_sensitive(True)
			self.prntbtn.set_sensitive(True)
			self.updateshare()

		self.update_printers()
		self.updateshare()
	def abtfunc(self,widget):
		global VERSION
		x=gtk.AboutDialog()
		x.set_version(VERSION)
		x.set_name("Smb-Admin")
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
		x.set_license("This program was designed to assist users\nin managing samba settings, shares and users.\n\
Copyright (C) <2007>  <David Brakers>\n\
This program is free software; you can redistribute it and/or modify\n\
it under the terms of the GNU General Public License as published by\n\
the Free Software Foundation; either version 2 of the License, or\n\
(at your option) any later version.\n\
\n\
This program is distributed in the hope that it will be useful,\n\
but WITHOUT ANY WARRANTY; without even the implied warranty of\n\
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n\
GNU General Public License for more details.\n\
\n\
You should have received a copy of the GNU General Public License along\n\
with this program; if not, write to the Free Software Foundation, Inc.,\n\
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.\n\
\n\
On a Debian GNU/Linux system you can find a copy of this license in\n\
`/usr/share/common-licenses/'.")
		x.set_comments(_("This program was designed to assist users in managing samba settings, shares and users."))
		x.show()
	def activate_print_sel(self,widget):
		self.mod_printer(None,None,None)	
	def activate_share_sel(self,widget):
		self.share_selected(None,None,None)
	def add_share_activate(self,widget):
		print "add share activated"
		print self.sh_entry.get_text()
		global ORIGINAL_SHARE
		ORIGINAL_SHARE=self.sh_entry.get_text()
		if self.sh_entry.get_text().strip() =="homes":
			self.local_entry.set_sensitive(False)
			self.local_btn.set_sensitive(False)
			self.share_info.set_text(_("Info: \"homes\" is a special setting that shares the home directory of each user."))

		else:
			self.share_info.set_text("")
			self.local_entry.set_sensitive(True)
			self.local_btn.set_sensitive(True)
		self.sharbox_list.hide()
		self.addsharbox.show()
	def add_share_deactivate(self,widget):
		self.sharbox_list.show()
		self.addsharbox.hide()
		self.share_clear(None)

	def add_share(self,widget):
		state=[]
		global ORIGINAL_SHARE
		if ORIGINAL_SHARE != "":
			del config[ORIGINAL_SHARE]
		for item in [self.browseable_sel,self.write_sel,self.avail_sel,self.pub_sel,self.follow_sel]:
			type=item.get_active()
			if type ==False:
				type="no"
			else:
				type="yes"
			state.append(type)
		sharename=self.sh_entry.get_text().strip()
		if sharename.strip()=="":
			return self.msgbox(_("Please enter a sharename."))
		elif self.local_entry.get_text().strip()=="":
			if sharename.strip() !="homes":
				return self.msgbox(_("Please enter a share path."))
		if sharename not in config.keys():
			config[sharename]={}
		if sharename.strip() !="homes":
			config[sharename]["path"]=self.local_entry.get_text()
		elif "path" in config[sharename]:
			del config[sharename]["path"]
		config[sharename]["comment"]=self.comment_entry.get_text()
		if self.valuser_entry.get_text().strip()!="":
			validusers=self.valuser_entry.get_text().strip().split(",")
			config[sharename]["valid users"]=validusers
			print validusers,"    <<<"
		elif "valid users" in config[sharename]:
			del config[sharename]["valid users"]
		config[sharename]["browseable"]=state[0]
		config[sharename]["writeable"]=state[1]
		config[sharename]["available"]=state[2]
		config[sharename]["public"]=state[3]
		config[sharename]["follow symlinks"]=state[4]
		print sharename
		if "path" in config[sharename]:
			print "path = ",config[sharename]["path"]
		print "browseabel = ",config[sharename]["browseable"]
		print "writeable = ",config[sharename]["writeable"]
		print "available = ",config[sharename]["available"]
		print "public = ",config[sharename]["public"]
		
		self.share_clear(None)
		self.add_share_deactivate(None)
		return gui.updateshare()
	def add_user_cmd(self,widget):
		pw1=self.pw_entry2.get_text()
		pw2=self.pw_entry3.get_text()
		user=self.uname_entry2.get_text().strip()
		pdb=subp.Popen("pdbedit -t -a "+user,shell=True,stdin=subp.PIPE,stdout=subp.PIPE,stderr=subp.PIPE)
		pdb.stdin.write(pw1+"\n")
		pdb.stdin.write(pw2+"\n")
		output_str=''
		errors_str=''
		output=pdb.stdout.readlines()
		errors=pdb.stderr.readlines()
		for line in output:
			output_str=output_str+line
		for line in errors:
			errors_str=errors_str+line
		if errors == []:
			print "no errors, show output"
			self.msgbox(output_str)#str(output).strip("\'[").strip("]\'").strip("\n"))
		else:
			print "errors present, show errors"
			self.msgbox(_("Error adding user")+" \'"+user+"\':\n"+errors_str)#str(errors).strip("\'[").strip("]\'").strip("\n"))
		self.unpw2.destroy()
		#return gui.updateusers(None)
		udt=UDU_thread()
		udt.setDaemon(1)
		udt.start()
	def chpw(self,widget):
		pw1=self.pw_entry2.get_text()
		pw2=self.pw_entry3.get_text()
		s = self.usertreeview.get_selection()
		(ls, iter) = s.get_selected()
		if iter is None:
			print "nothing selected"
		else:
			user=ls.get_value(iter,1)
			if pw1==pw2:
				pdb=subp.Popen("smbpasswd -s "+user,shell=True,stdin=subp.PIPE,stdout=subp.PIPE,stderr=subp.PIPE)
				pdb.stdin.write(pw1+"\n")
				pdb.stdin.write(pw2+"\n")
				if pdb.stderr.readlines() ==[]:
					print "NO ERRORS"
					self.msgbox(_("Successfully changed the password")+str(pdb.stdout.readlines()))
				else:
					print pdb.stderr.readlines()
			else:
				return self.msgbox(_("The passwords dont match."))

		self.unpw2.destroy()
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
			del config[sharename]
			self.share_clear("worthless data")
		gui.updateshare()
	def folder_sel(self,widget):	
		filew = gtk.FileChooserDialog(title=_("Choose a folder"),action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
			buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
		response=filew.run()
		if response ==gtk.RESPONSE_OK:
			self.local_entry.set_text(filew.get_filename())
		filew.destroy()
	
	def homes_toggle(self,widget):
		print "homes toggle"
		if self.homes_sel.get_active()==True:
			if "homes" in config.keys():
				print "present.. exiting."
			else:
				config["homes"]={}
				config["homes"]["browseable"]="no"
				config["homes"]["writeable"]="yes"
				config["homes"]["available"]="yes"
				config["homes"]["public"]="no"
				config["homes"]["follow symlinks"]="yes"
				config["homes"]["comment"]=_("Shared user home directories")
		elif self.homes_sel.get_active()==False:
			if "homes" in config.keys():
				del config["homes"]
			print "unchecked"
		self.updateshare()
	def kill_pr(self,widget):
		self.sep_lbl.show()
		self.psharetreeview.show()
		self.print_hbbox.show()
		self.vbox_pr.hide()
	def kill(self,widget):
		self.unpw2.hide()
	def load(self,printername):
		self.pr_comment.set_text(config[printername]["comment"])
		if "valid users" in config[printername]:
			users=""
			if config[printername]["valid users"] != "":
				for x in config[printername]["valid users"]:
					users=users+x+","
			self.pr_users.set_text(users.strip(","))
		if "browseable" in config[printername]:	
			if config[printername]["browseable"].lower()=="yes":
				self.pbrowseable_sel.set_active(True)
			else:
				self.pbrowseable_sel.set_active(False)
		else: 
			self.pbrowseable_sel.set_active(True)
		if "available" in config[printername]:	
			if config[printername]["available"].lower()=="yes":
				self.pavail_sel.set_active(True)
			else:
				self.pavail_sel.set_active(False)
		else:
			self.pavail_sel.set_active(True)
		if "public" in config[printername]:
			if config[printername]["public"].lower()=="yes":
				self.ppub_sel.set_active(True)
			else:
				self.ppub_sel.set_active(False)
		else:
			self.ppub_sel.set_active(True)
	def localmb_func(self,widget):
		if self.localmb_sel.get_active()==True:
			config["global"]["local master"]="yes"
		elif self.localmb_sel.get_active()==False:
			config["global"]["local master"]="no"
	def mod_printer(self,x,y,widget):
		s = self.psharetreeview.get_selection()
		(ls, iter) = s.get_selected()
		if iter is None:
			print "nothing selected"
		else:
			self.pr_comment=gtk.Entry()
			#self.pr_comment.
			self.pr_users=gtk.Entry()
			self.sep_lbl.hide()
			self.psharetreeview.hide()
			self.print_hbbox.hide()
			printername=ls.get_value(iter,1)
#			print config[printername]
			comment_lbl=gtk.Label(_("Comment:"))

			cancel_btn=gtk.Button(stock=gtk.STOCK_CANCEL)
			cancel_btn.connect("clicked",self.kill_pr)
			ok_btn=gtk.Button(stock=gtk.STOCK_OK)
			ok_btn.connect("clicked",self.mod_pr_cmd)
						
			self.pbrowseable_sel= gtk.CheckButton(_("Visible on clients"),True)
			self.pavail_sel= gtk.CheckButton(_("Enabled"),True)
			self.ppub_sel= gtk.CheckButton(_("Open to the Public"),False)
			self.ppub_sel.connect("clicked", self.public_pr)
			pvaluser_lbl=gtk.Label(_("Valid Users (optional)"))
			self.pr_lbl=gtk.Label(_("Settings for ")+printername)
			#comment_lbl=gtk.Label("Comment")
			
			self.vbox_pr=gtk.VBox()
			hbox1=gtk.HButtonBox()
			hbox=gtk.HButtonBox()
			hbox2=gtk.HButtonBox()
			
			hbox1.pack_start(comment_lbl)
			hbox1.pack_start(self.pr_comment)
			self.vbox_pr.pack_start(self.pr_lbl)
			self.vbox_pr.pack_start(hbox1)
			self.vbox_pr.pack_start(self.pbrowseable_sel)
			self.vbox_pr.pack_start(self.pavail_sel)
			self.vbox_pr.pack_start(self.ppub_sel)
			hbox.pack_start(pvaluser_lbl)
			hbox.pack_start(self.pr_users)
			hbox2.pack_start(cancel_btn)
			hbox2.pack_start(ok_btn)
			
			self.vbox_pr.pack_start(hbox)
			self.vbox_pr.pack_start(hbox2)
#			print config[printername]["comment"]
			self.print_box.pack_start(self.vbox_pr)
			self.vbox_pr.show_all()
			self.load(printername)
	def mod_pr_cmd(self,widget):
		print "command executed ###########################"
		printername=self.pr_lbl.get_text().lstrip("Settings for ")
		print config[printername]
		state=[]
		for item in [self.pbrowseable_sel,self.pavail_sel,self.ppub_sel]:
			type=item.get_active()
			if type ==False:
				type="no"
			else:
				type="yes"
			state.append(type)
			print state
		if self.pr_users.get_text().strip()!="":
			validusers=self.pr_users.get_text().strip().split(",")
			config[printername]["valid users"]=validusers
			print validusers,"    <<<"
		elif "valid users" in config[printername]:
			del config[printername]["valid users"]
		config[printername]["comment"]=self.pr_comment.get_text()
		config[printername]["path"]="/var/spool/samba"
		config[printername]["printing"]="cups"
		config[printername]["printcap"]="cups"
		config[printername]["printer name"]=printername
		config[printername]["browseable"]=state[0]
		config[printername]["available"]=state[1]
		config[printername]["public"]=state[2]
		config[printername]["printable"]="yes"
		print "done"
		gui.updateshare()
		self.update_printers()
		self.sep_lbl.show()
		self.psharetreeview.show()
		self.print_hbbox.show()
		self.vbox_pr.hide()
	def msgbox(self,MSG):
		popup = gtk.MessageDialog(parent=None, flags=gtk.MESSAGE_WARNING, buttons=gtk.BUTTONS_OK, message_format=MSG)
		popup.set_position(gtk.WIN_POS_CENTER_ALWAYS)
		popup.show_all()
		popup.run()
		popup.destroy()
		return True
	def prefmb_func(self,widget):
		if self.prefmb_sel.get_active()==True:
			config["global"]["preferred master"]="yes"
		elif self.prefmb_sel.get_active()==False:
			config["global"]["preferred master"]="no"
	def public_share(self,widget):
		if self.pub_sel.get_active() == True:
			self.valuser_entry.set_sensitive(False)
			self.valuser_entry.set_text("")
		else:
			self.valuser_entry.set_sensitive(True)
	def public_pr(self,widget):
		if self.ppub_sel.get_active() == True:
			self.pr_users.set_sensitive(False)
			self.pr_users.set_text("")
		else:
			self.pr_users.set_sensitive(True)
	def read_conf(self):
		print config
		print "#####################"
		print "reading configuration and applying settings"
		if "netbios name" in config["global"]:
			self.nb_name_entry.set_text(config["global"]["netbios name"])
		if "workgroup" in config["global"]:
			self.wg_entry.set_text(config["global"]["workgroup"])
		if "server string" in config["global"]:
			self.serverstr_entry.set_text( str(config['global']['server string']).strip("['").strip("']"))
		if "preferred master" in config["global"]:
			if config["global"]["preferred master"].lower() in ["true","yes"]:
				self.prefmb_sel.set_active(True)
			elif config["global"]["preferred master"].lower() in ["false","no"]:
				self.prefmb_sel.set_active(False)
		if "local master" in config["global"]:
			if config["global"]["local master"].lower() in ["true","yes"]:
				self.localmb_sel.set_active(True)
			elif config["global"]["local master"].lower() in ["false","no"]:
				self.localmb_sel.set_active(False)
		if "usershare allow guests" in config["global"]:
			print "allow guests ="+config["global"]["usershare allow guests"].lower()
			if config["global"]["usershare allow guests"].lower() in ["true","yes"]:
				self.usershare_allow_guest.set_active(True)
			elif config["global"]["usershare allow guests"].lower() in ["false","no"]:
				self.usershare_allow_guest.set_active(False)
		else:
			self.usershare_allow_guest.set_active(False)
		if "usershare owner only" in config["global"]:
			if config["global"]["usershare owner only"].lower() in ["true","yes"]:
				self.usershare_owner_only.set_active(True)
			elif config["global"]["usershare owner only"].lower() in ["false","no"]:
				self.usershare_owner_only.set_active(False)
		else:
			self.usershare_owner_only.set_active(False)
		if "usershare max shares" in config["global"]:
			if config["global"]["usershare max shares"]:
				self.usershare_max_shares_entry.set_text(config["global"]["usershare max shares"])
		else:
			self.usershare_max_shares_entry.set_text("100")
		if "os level" in config["global"]:
			self.oslvl_entry.set_text(config["global"]["os level"])
		if "wins server" in config["global"]:
			print "wins server"
			self.winserv_entry.set_text(config["global"]["wins server"])
			config["global"]["wins support"]="no"
			self.winserv_sel3.set_active(True)
		elif "wins support" not in config["global"]:
			print "setting winserv sel true"
			self.winserv_sel.set_active(True)
			self.winserv_entry.set_sensitive(False)
			self.winserv_entry.set_text("")
		if "wins support" in config["global"]:
			self.winserv_entry.set_sensitive(False)
			self.winserv_entry.set_text("")
			if config["global"]["wins support"].lower() in ["false","no"]:
				print "wins support no"
				self.winserv_sel.set_active(True)
			elif config["global"]["wins support"].lower() in ["true","yes"]:
				print "wins support yes"
				self.winserv_sel2.set_active(True)
			#del config["global"]["wins server"]
		for key in config.keys():
			if key.lower()=="homes":
				self.homes_sel.set_active(True)
			


	def remove_printer(self,widget):
		sharename=""
		s = self.psharetreeview.get_selection()
		(ls, iter) = s.get_selected()	
		if iter is None:
			print "nothing selected"
		else:
			sharename=ls.get_value(iter, 1)
		if sharename !="":
			print sharename
			del config[sharename]
			#self.share_clear("worthless data")
		gui.updateshare()
		self.update_printers()
	def restart_server(self,widget):
		def restart():
			print "restarting servers"
			global RESTART_CMD
			#~ if os.access("/etc/init.d/samba",os.X_OK):
				#~ rsserver=os.system("/etc/init.d/samba restart")
			#~ elif os.access("/etc/init.d/smb",os.X_OK):
				#~ rsserver=os.system("/etc/init.d/smb restart")
			rsserver=os.system(RESTART_CMD)
		if compare_conf== config:
			return restart()
		else: 
		#def sub_func():
			msg=_("Changes have been made. Would you like to save before restarting the server?")
			x=gtk.MessageDialog(parent=None, flags=0, buttons=gtk.BUTTONS_YES_NO, message_format=msg)
			x.set_position(gtk.WIN_POS_CENTER_ALWAYS)
			x.show_all()
			response = x.run()
			if response == gtk.RESPONSE_YES:
				self.save_config(None)
				restart()
			elif response== gtk.RESPONSE_NO:
				restart()
			x.destroy()
			print "configuration has changed. Would you like to save it first?"
	def restore_conf(self,widget):
		global config
		config=configobj.ConfigObj(orig_config)
		self.read_conf()
		gui.updateshare()
		if "printers" not in config.keys():
			self.shall_prnt.set_active(False)
		elif "printers" in config.keys():
			self.shall_prnt.set_active(True)
			#del orig_config["global"]["wins server"]
	
	def save_config(self,widget):
		global compare_conf
		print "saving configurations"
		list=[]
		run=False
		for item in config.keys():
			if item != "global":
				list.append(item)
		for share in list:
			if "public" in config[share]:
				if config[share]["public"].lower() in ["true","yes"]:
					run=True
		if run==True:
			msg=_("In order for a Windows client to access a share as guest, the \"map to guest\" option needs to be set. Do you wish to set it now?")
			if "map to guest" not in config["global"]:
				x=gtk.MessageDialog(parent=None, flags=0, buttons=gtk.BUTTONS_YES_NO, message_format=msg)
				x.set_position(gtk.WIN_POS_CENTER_ALWAYS)
				x.show_all()
				response = x.run()
				if response == gtk.RESPONSE_YES:
					print "yes"
					config["global"]["map to guest"]="bad user"
				elif response== gtk.RESPONSE_NO:
					print "well ok then so much for windows users"
				x.destroy()
		if self.winserv_sel3.get_active()==True:
			print self.winserv_sel3.get_active()
			config["global"]["wins server"]=self.winserv_entry.get_text()
		elif "wins server" in config["global"]:
			del config["global"]["wins server"]
		config["global"]["netbios name"]=self.nb_name_entry.get_text()
		config["global"]["os level"]=self.oslvl_entry.get_text()
		config["global"]["workgroup"]=self.wg_entry.get_text().upper()
		config["global"]["server string"]=self.serverstr_entry.get_text()
		config["global"]["usershare max shares"]=self.usershare_max_shares_entry.get_text()
		if self.usershare_owner_only.get_active()==True:
			print "its true"
			config["global"]["usershare owner only"]="yes"
		elif self.usershare_owner_only.get_active()==False:
			print "its false"
			config["global"]["usershare owner only"]="no"
		if self.usershare_allow_guest.get_active() == True:
			print "from save, guests = true"
			config["global"]["usershare allow guests"]="yes"
		elif self.usershare_allow_guest.get_active() == False:
			print "from save, guests = false"
			config["global"]["usershare allow guests"]="no"

		config.filename="/etc/samba/smb.conf"
		config.write()
		compare_conf=configobj.ConfigObj(config)
		return self.read_conf()

	def share_selected(self,x,y,widget):
#		print y[0]#y[0] returns the number of the item in the list
		s = self.sharetreeview.get_selection()
		(ls, iter) = s.get_selected()	
		if iter is None:
			print "nothing selected"
			return
		else:
			sharename=ls.get_value(iter, 1)
		print sharename+" selected"
		self.sh_entry.set_text(sharename)
		if sharename.lower() != "homes":
			self.local_entry.set_text(config[sharename]["path"])
		if "comment" in config[sharename]:
			self.comment_entry.set_text(config[sharename]["comment"])
		else:
			self.comment_entry.set_text("")
		if "follow symlinks" in config[sharename]:
			print "yes it is"
			if config[sharename]["follow symlinks"].lower() in ["true","yes"]:
				self.follow_sel.set_active(True)
			else:
				self.follow_sel.set_active(False)			
		if "valid users" in config[sharename]:
			print config[sharename]["valid users"]
			print "valid users"
			print config[sharename]["valid users"]
			valusers=''
			if type(config[sharename]["valid users"]).__name__=="list":
				for item in config[sharename]["valid users"]:
					if item != "":
						valusers=valusers+item+","
				valusers=valusers.strip(",")
				self.valuser_entry.set_text(valusers)
			elif type(config[sharename]["valid users"]).__name__=="str":
				valusers=config[sharename]["valid users"].strip(",")
			self.valuser_entry.set_text(valusers)
		if "browseable" in config[sharename]:
			if config[sharename]["browseable"].lower() in ["true","yes"]:
				self.browseable_sel.set_active(True)
			else:
				self.browseable_sel.set_active(False)		
		if "writeable" in config[sharename]:
			if config[sharename]["writeable"].lower() in ["true","yes"]:
				self.write_sel.set_active(True)
			else:
				self.write_sel.set_active(False)
		if "available" in config[sharename]:
			if config[sharename]["available"].lower() in ["true","yes"]:
				self.avail_sel.set_active(True)
			else:
				self.avail_sel.set_active(False)
		if "public" in config[sharename]:
			if config[sharename]["public"].lower() in ["true","yes"]:
				self.pub_sel.set_active(True)
			else:
				self.pub_sel.set_active(False)
		self.add_share_activate(None)
	
	def share_clear(self,widget):
		self.sh_entry.set_text("")
		self.local_entry.set_text("")
		self.valuser_entry.set_text("")
		self.comment_entry.set_text("")
		self.browseable_sel.set_active(True)
		self.write_sel.set_active(False)
		self.follow_sel.set_active(True)
		self.avail_sel.set_active(True)
		self.pub_sel.set_active(False)
	def tab_clicked(self,widget,x,pagenum):
		def sub_func():
			msg=_("Smb-Admin needs to set the \"printing\" and \"printcap name\" to \"cups\" to allow CUPS print sharing. Do you wish to do this?")
			x=gtk.MessageDialog(parent=None, flags=0, buttons=gtk.BUTTONS_YES_NO, message_format=msg)
			x.set_position(gtk.WIN_POS_CENTER_ALWAYS)
			x.show_all()
			response = x.run()
			if response == gtk.RESPONSE_YES:
				config["global"]["printcap name"]="cups"
				config["global"]["printing"]="cups"
				self.shall_prnt.show()
				self.prnt_scw.show()
				self.prntbtn.show()
				self.sep_lbl.show()
				self.psharetreeview.show()
				self.print_hbbox.show()
				self.print_box.set_sensitive(True)
				self.update_printers()
			elif response== gtk.RESPONSE_NO:
				self.print_box.set_sensitive(False)
#				prnt_lbl.hide()
				self.shall_prnt.hide()
				self.prnt_scw.hide()
				self.prntbtn.hide()
				self.sep_lbl.hide()
				self.psharetreeview.hide()
				self.print_hbbox.hide()
			x.destroy()
		def auto_set():
			print "auto set running"
			config["global"]["printcap name"]="cups"
			config["global"]["printing"]="cups"
			self.shall_prnt.show()
			self.prnt_scw.show()
			self.prntbtn.show()
			self.sep_lbl.show()
			self.psharetreeview.show()
			self.print_hbbox.show()
			self.print_box.set_sensitive(True)
		def passdb_func():
			x=gtk.MessageDialog(parent=None, flags=0, buttons=gtk.BUTTONS_YES_NO, message_format=msg)
			x.set_position(gtk.WIN_POS_CENTER_ALWAYS)
			x.show_all()
			response = x.run()
			if response == gtk.RESPONSE_YES:
				config["global"]["passdb backend"]="smbpasswd"
				self.save_config(self)
				self.restart_server(self)
			elif response== gtk.RESPONSE_NO:
				self.users_box2.set_sensitive(False)
			x.destroy()
		if pagenum==2:
			self.users_box2.set_sensitive(True)
			if "passdb backend" not in config["global"]:
				passdb_func()
			#gui.updateusers(None)
			udt=UDU_thread()
			udt.setDaemon(1)
			udt.start()
		elif pagenum==3:
			if "printcap name" not in config["global"]:
				print "no printcap name set... running auto set"
				auto_set()
			elif config["global"]["printcap name"].lower() !="cups":
				return sub_func()
			if "printing" not in config["global"]:
				print "no printing set... running auto set"
				return auto_set()
			elif config["global"]["printing"].lower()  !="cups":
				return sub_func()
			print "now to update printer list"
			self.update_printers()
			if "load printers" in config["global"]:
				if config["global"]["load printers"].lower() in ["true","yes"]:
					self.shall_prnt.set_active(True)
				elif config["global"]["load printers"].lower() in ["false","no"]:
					self.shall_prnt.set_active(False)
			print "updateing"
			self.update_printers()
	def toggle_printer(self,widget):
		s = self.prntsharetreeview.get_selection()
		(ls, iter) = s.get_selected()
		if iter is None:
			pass #print "nothing selected"
		else:
			printername=ls.get_value(iter,1)
#			print printername
#			print ls.get_value(iter,2)
			if ls.get_value(iter,2).lower()=="yes":
#				print "stop shareing printer "+printername
				del config[printername]
				self.update_printers()
				gui.updateshare()
			elif ls.get_value(iter,2).lower()=="no":
				if printername not in config.keys():
					config[printername]={}
				config[printername]["comment"]=_("Shared printer ")+printername
				config[printername]["path"]="/var/spool/samba"
				config[printername]["printing"]="cups"
				config[printername]["printcap"]="cups"
				config[printername]["printer name"]=printername
				config[printername]["writeable"]="no"
				config[printername]["printable"]="yes"
				config[printername]["available"]="yes"
				config[printername]["public"]="no"
				config[printername]["browseable"]="yes"
				self.update_printers()
				gui.updateshare()
	def unamepw(self,data,MSG):
		unamelbl2=gtk.Label(_("User Name"))
		ok2=gtk.Button(stock=gtk.STOCK_OK)
		info_label=gtk.Label(MSG)
		self.pw_entry2.set_visibility(False)
		self.pw_entry3.set_visibility(False)
		self.pw_entry2.set_invisible_char("*") 
		self.pw_entry3.set_invisible_char("*") 
		
		pwlbl2=gtk.Label(_("Password"))
		pwlbl3=gtk.Label(_("Password Again"))
		pwbox=gtk.VButtonBox()
		cancel2=gtk.Button(stock=gtk.STOCK_CANCEL)
		bbox2=gtk.HButtonBox()
		bbox2.pack_start(cancel2,False,False, 0)
		bbox2.pack_start(ok2,False,False, 0)
		box2=gtk.VBox()
		box2.pack_start(info_label,False, True, 0)
		box2.pack_start(pwbox,False,False,0)
		box2.pack_end(bbox2,True,False,0)
		cancel2.connect("clicked",self.kill)
		self.unpw2.set_position(gtk.WIN_POS_CENTER_ALWAYS)	

		if data=="add":
			pwbox.pack_start(unamelbl2,False, True, 0)
			pwbox.pack_start(self.uname_entry2,False, True, 0)
			pwbox.pack_end(pwlbl2,False, True, 0)
			pwbox.pack_end(self.pw_entry2,True, True, 0)
			pwbox.pack_end(pwlbl3,False, True, 0)
			pwbox.pack_end(self.pw_entry3,True, True, 0)
			ok2.connect("clicked",self.add_user_cmd)
		elif data=="changepw":
			pwbox.pack_end(pwlbl2,False, True, 0)
			pwbox.pack_end(self.pw_entry2,True, True, 0)
			pwbox.pack_end(pwlbl3,False, True, 0)
			pwbox.pack_end(self.pw_entry3,True, True, 0)
			ok2.connect("clicked",self.chpw)	
		self.unpw2.add(box2)
		self.unpw2.show_all()
	def user_func(self,widget,data):
		s = self.usertreeview.get_selection()
		(ls, iter) = s.get_selected()
		if iter is None:
			print "nothing selected"
		else:
			username=ls.get_value(iter,1)
			if data=="del":
				x=gtk.MessageDialog(parent=None, flags=0, buttons=gtk.BUTTONS_YES_NO, message_format=_("Are you sure you want to delete user: ")+username)
				x.set_position(gtk.WIN_POS_CENTER_ALWAYS)
				x.show_all()
				response = x.run()
				if response == gtk.RESPONSE_YES:
					print "deleting user: "+username
					cx=os.popen("pdbedit -x "+username)
					cx.close()
				elif response== gtk.RESPONSE_NO:
					print "Not deleting user: "+username
				x.destroy()
			elif data=="toggle":
				file=os.popen("pdbedit -Lv -u "+username)
				for line in file:
					if line.startswith(_("Account Flags")):
						flags=line.split("[")[1].strip().strip("]").strip()
						flags=flags.strip("TUMWSI")
				file.close()
				print flags
				if ls.get_value(iter,2)=="Enabled":
					flags="D"+flags
					print flags+"<<<<FLAGS for disable"
					print ("pdbedit -c \"["+flags+"]\" -u "+username)
					x=os.popen("pdbedit -c \"["+flags+"]\" -u "+username)
					x.close()
				elif ls.get_value(iter,2)=="Disabled":
					flags=flags.replace("D","")
					print flags+"<<<<< FLAGS for enable"
					print ( "pdbedit -c \"["+flags+"]\" -u  "+username)
					x=os.popen( "pdbedit -c \"["+flags+"]\" -u  "+username)
					x.close()
			elif data=="changepw":
				return self.unamepw(data,_("Please enter the new passwords for ")+username)
			#gui.updateusers(None)
			udt=UDU_thread()
			udt.setDaemon(1)
			udt.start()
		if data=="add":
			return self.unamepw(data,_("To add a samba user, please enter the following:"))
			udt=UDU_thread()
			udt.setDaemon(1)
			udt.start()
			#gui.updateusers(None)


	def update_printers(self):
		print "UPDATING THE PRINTERS"
		dictop={}
		if os.access("/etc/cups/printers.conf",os.R_OK)==True:
			print "access granted"
			printers_file=open("/etc/cups/printers.conf")
			printer_name=""
			shared_state=""
			place=0
			dictop={}
#			printers_file=open("printers.conf")
			printers=printers_file.readlines()
			for line in printers:
				if line.split()[0] in ["<Printer","<DefaultPrinter"]:
					printer_name=line.split()[1].strip(">")
					dictop[place]={}
					dictop[place]["name"]=printer_name
				elif line.startswith("Shared"):
					shared_state=line.split()[1]
					dictop[place]["cups_share_state"]=shared_state
				elif line.startswith("</Printer"):
					place=place+1
			for x in dictop.keys():
				if "cups_share_state" not in dictop[x]:
					print "missing"
					dictop[x]["cups_share_state"]="missing"
			printers_file.close()
			z=0
			self.prntsharelist.clear()
			for item in dictop.keys():
				printer=dictop[item]["name"]
				if self.shall_prnt.get_active()==True:
					smbshare="yes"
				elif printer in config.keys():
					smbshare="yes"
				else:
					smbshare="no"
				iter = self.prntsharelist.append([z,printer,smbshare])#,dictop[printer]])
				z=z+1
			if "printers" in config.keys():
				self.shall_prnt.set_active(True)
				#self.set_prnt()
			else:
				self.shall_prnt.set_active(False)
	def updateusers(self,widget):
		self.show_allusers.set_sensitive(False)
		users=[]
		gtk.gdk.threads_enter()
		self.userlist.clear()
		gtk.gdk.threads_leave()
		for line in os.popen("pdbedit -L"):
			user=line.split(":")[0]
			y=0
			STATUS="";pw_set=""
			info=os.popen("pdbedit -Lv -u "+user)
			for line in info:
				if "Flags" in line:
					line2=line.split("[")[1].strip().strip("]").strip()
					STATUS=""
					if "D" in line2:
						STATUS="Disabled"
					else:
						STATUS="Enabled"
				if line.startswith("Password last set"):
					pw_set=line.split(":",1)[1]
			if pw_set.strip() == "0":
				if self.show_allusers.get_active()==True:
					gtk.gdk.threads_enter()
					iter = self.userlist.append( [y,user,STATUS,pw_set.strip()] )
					gtk.gdk.threads_leave()
					y=y+1
			else:
				gtk.gdk.threads_enter()
				iter = self.userlist.append( [y,user,STATUS,pw_set.strip()] )
				gtk.gdk.threads_leave()
				y=y+1
		self.show_allusers.set_sensitive(True)
	def updateshare(self):
		self.sharelist.clear()
		self.psharelist.clear()
		z=0
		y=0
		pshares=[]
		shares2=[]
		comment=[]
		pcomment=[]
		readonly=[]
		avail=[]
		pavail=[]
		path=[]
		browseable=[]
		pbrowseable=[]
		ppublic=[]
		public=[]
		shares=config.keys()
		for item in shares:
			item=item.strip()
			if item not in ["global"]:
				if "printable" in config[item]:
					if config[item]["printable"].lower() in ["true","yes"]:
						try:
							pcomment.append(config[item]["comment"])
						except:
							pcomment.append("")
						try:
							ppublic.append(config[item]["public"])
						except:
							try:
								ppublic.append(config["global"]["public"])
							except:
								ppublic.append("yes")
						try:
							pavail.append(config[item]["available"])
						except:
							try:
								pavail.append(config["global"]["available"])
							except:
								pavail.append("yes")
						try:
							pbrowseable.append(config[item]["browseable"])
						except:
							try:
								pbrowseable.append(config["global"]["browseable"])
							except:
								pbrowseable.append("yes")
						pshares.append(item)
						iter1 = self.psharelist.append( [y,pshares[y],pcomment[y],pbrowseable[y],pavail[y],ppublic[y]])
						y=y+1
				else:
					try:
						comment.append(config[item]["comment"])
					except:
						comment.append("")
					try:
						public.append(config[item]["public"])
					except:
						try:
							public.append(config["global"]["public"])
						except:
							public.append("no")
					try:
						readonly.append(config[item]["writeable"])
					except:
						try:
							readonly.append(config["global"]["writeable"])
						except:
							readonly.append("no")
					try:
						avail.append(config[item]["available"])
					except:
						try:
							avail.append(config["global"]["available"])
						except:
							avail.append("yes")
					try:
						browseable.append(config[item]["browseable"])
					except:
						try:
							browseable.append(config["global"]["browseable"])
						except:
							browseable.append("yes")
					try:
						path.append(config[item]["path"])
					except:
						path.append("")
					
					#name=(shares2[z])
					shares2.append(item)
					iter = self.sharelist.append( [z,shares2[z],comment[z],browseable[z],avail[z],readonly[z],public[z],path[z]] )
					z=z+1
	


	def winserv_func(self,widget,data):
		print self.winserv_sel3.get_active()
		print data
		if self.winserv_sel3.get_active()==True:
			self.winserv_entry.set_sensitive(True)
		else:
			self.winserv_entry.set_sensitive(False)
			self.winserv_entry.set_text("")
			
		if data=="yes":
			config["global"]["wins support"]="yes"
		elif data=="no":
			config["global"]["wins support"]="no"
		else:
			config["global"]["wins server"]=self.winserv_entry.get_text()
			config["global"]["wins support"]="no"






def udu_start(Nothing):
	udt=UDU_thread()
	udt.setDaemon(1)
	udt.start()
gui=GUI()
#if ERROR_OUTPUT:
#	gui.msgbox("An error occured while importing smb.conf.\n"+str(ERROR_OUTPUT))
gui.updateshare()
gui.share_clear(None)
gui.read_conf()
gtk.gdk.threads_init()
class UDU_thread(threading.Thread):
	def run(self):
		gui.updateusers(None)
class MAIN(threading.Thread):
	def __init__(self):
		gtk.main()
main=MAIN()
#gtk.main()
