import re
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import sys
from player import Player

file = open(sys.argv[1])
gb_data = tuple(file.read().split('\n'))
file.close()
captured_data = {}
captured_data["players"] = {}
player_names = []

player_capture_mode = False

def create_team_data(data, is_visitor):
    team_data = {}
    if is_visitor:
        teamname_record = data.split("VISITOR: ")[1].split("(")
    else:
        teamname_record = data.split("HOME: ")[1].split("(")
    teamname_record[0] = teamname_record[0][:-1]
    teamname_record[1] = teamname_record[1].replace(")","")
    
    team_data["name"] = teamname_record[0]
    team_data["record"] = teamname_record[1]
    team_data["name_short"] = data.split(" ")[-2]
    return team_data

#add visiting players
for x in gb_data:
    is_minute = len(x.split(" ")[0].split(":"))
    if x.startswith("VISITOR"):
        captured_data["visitors"] = create_team_data(x,True)    
        player_capture_mode = True
        # second condition - after box scores there are minutes in 240:00 format
    elif player_capture_mode and is_minute!=2 and not(x.startswith("POS")):                 
        captured_player = Player(x,True)
        if captured_player.status == "active":
            if captured_player.pbp_name in player_names:
                raise Exception("please change the name in the box score (Jaylen/Jaylin Williams type name issue)")
            else:
                player_names.append(captured_player.pbp_name)
                captured_data["players"][captured_player.pbp_name] = captured_player
    elif player_capture_mode and is_minute==2:  
        player_capture_mode = False
        break
    
# add home players
for x in gb_data:
    is_minute = len(x.split(" ")[0].split(":"))
    if x.startswith("HOME"):
        captured_data["home"] = create_team_data(x,False)    
        player_capture_mode = True
        # second condition - after box scores there are minutes in 240:00 format
    elif player_capture_mode and is_minute!=2 and not(x.startswith("POS")):                 
        captured_player = Player(x,False)
        if captured_player.status == "active":
            if captured_player.pbp_name in player_names:
                raise Exception("please change the name in the box score (Jaylen/Jaylin Williams type name issue)")
            else:
                player_names.append(captured_player.pbp_name)
                captured_data["players"][captured_player.pbp_name] = captured_player
    elif player_capture_mode and is_minute==2:  
        player_capture_mode = False
        break
    
    
def timer_converter(time,offset, period_duration_sec):
    t = time.split(":")
    
    if '.' not in time:
        minutes_remaining = int(t[0])
        seconds_remaining = int(t[1])
        return offset+(period_duration_sec-60*minutes_remaining-seconds_remaining)
    else:
        s = t[1].split(".")
        seconds_remaining = int(s[0])
        ms_remaining = int(s[1])
        return offset+(period_duration_sec-seconds_remaining-ms_remaining/10)
    
visitors_just_shot = False
plusminus = 0
captured_data["pmlist"] = [(0,0)]
vis_score = 0
home_score = 0

def parse_pbp(pbpstr, time):
    global visitors_just_shot,plusminus,home_score,vis_score
    if "SUB: " in pbpstr:
        p = pbpstr.split("SUB: ")[1].split(" FOR ")
        captured_data["players"][p[0]].sub_in(time,plusminus)
        captured_data["players"][p[1]].sub_out(time,plusminus)
    elif "JUMP BALL" in pbpstr:
        pass
    elif "TIMEOUT" in pbpstr:
        pass
    elif "Coach's" in pbpstr:
        pass
    elif "FOUL" in pbpstr or "Offensive (P" in pbpstr or "Foul (P" in pbpstr:
        player = pbpstr.split(" ")[0]
        captured_data["players"][player].add_event(time,"F")
    elif "STEAL" in pbpstr:    
        split_by_to = pbpstr.split("TURNOVER")
        if "STEAL" in split_by_to[0]:
            split_by_steal = split_by_to[0].split(" STEAL ")
            captured_data["players"][split_by_steal[0]].add_event(time,"S")
            captured_data["players"][split_by_steal[1].split(" ")[0]].add_event(time,"↻")
        else:
            captured_data["players"][split_by_to[0].split(" ")[0]].add_event(time,"↻")
            captured_data["players"][split_by_to[1].split(" ")[-2]].add_event(time,"S")
    elif "TURNOVER" in pbpstr:
        player = pbpstr.split(" ")[0]
        if "." in player:
            captured_data["players"][player].add_event(time,"↻")  
        else:
            pass #team turnover
    elif "BLOCK" in pbpstr:
        split_by_block = pbpstr.split(" BLOCK")
        if "MISS" in split_by_block[0]:
            d = split_by_block[0].split(" ")
            blocker = d[-1]
            shooter = d[1]
        else:
            blocker = split_by_block[0]
            shooter = split_by_block[1].split(" ")[2]

        if captured_data["players"][shooter].is_visitor:
            visitors_just_shot = True
        else:
            visitors_just_shot = False
            
        captured_data["players"][blocker].add_event(time,"B")
        if "3PT" in pbpstr:
            captured_data["players"][shooter].add_event(time,"▽") 
        else:
            captured_data["players"][shooter].add_event(time,"X") 
    elif "MISS" in pbpstr:
        shooter = pbpstr.split(" ")[1]
        if captured_data["players"][shooter].is_visitor:
            visitors_just_shot = True
        else:
            visitors_just_shot = False
        if "3PT" in pbpstr:
            captured_data["players"][shooter].add_event(time,"▽") 
        elif "Free Throw" in pbpstr:
            captured_data["players"][shooter].add_event(time,"x") 
        else:
            captured_data["players"][shooter].add_event(time,"X") 
    elif "REBOUND" in pbpstr:
        player = pbpstr.split(" ")[0]
        if "." in player:
            if captured_data["players"][player].is_visitor:
                if visitors_just_shot:
                    captured_data["players"][player].add_event(time,"O") 
                else:
                    captured_data["players"][player].add_event(time,"D") 
            else:
                if visitors_just_shot:
                    captured_data["players"][player].add_event(time,"D") 
                else:
                    captured_data["players"][player].add_event(time,"O") 
        else:
            pass #team turnover
    elif "Violation" in pbpstr:
        player = pbpstr.split(" ")[0]
        if "." in player:
            captured_data["players"][player].add_event(time,"V")  
        else:
            pass #team violation
    elif "Technical Foul" in pbpstr:
        try:
            captured_data["players"][pbpstr.split(" (")[0].split(" ")[-1]].add_event(time,"T") 
        except:
            print(f'Tried giving tech to: {pbpstr.split(" (")[0].split(" ")[-1]}. coach or bug?')
    else:
        if re.search('[0-9]+\-[0-9]+',pbpstr) and "Possession" not in pbpstr:
            d = pbpstr.split(" ")
            assister = None

            if re.search('[0-9]+\-[0-9]+',d[0]):
                shooter = d[2]
                if "(" in pbpstr:
                    assister = d[-1].replace("(","").replace(")","")
            else:
                shooter = d[0]
                if "(" in pbpstr:
                    assister = d[-3].replace("(","").replace(")","")

            
                

            if assister:
                captured_data["players"][assister].add_event(time,"A")
            
            if "3PT" in pbpstr:
                points = 3
                captured_data["players"][shooter].add_event(time,"3")
            elif "Free Throw" in pbpstr:
                points = 1
                captured_data["players"][shooter].add_event(time,"1")
            else:
                points = 2
                captured_data["players"][shooter].add_event(time,"2")
                
            if captured_data["players"][shooter].is_visitor:
                plusminus += points
                vis_score += points
            else:
                plusminus -= points
                home_score += points
            captured_data["pmlist"].append((time,plusminus))    
        else:
            print(pbpstr)

#MAIN
capture = False
pbp = False
gamestart = False
period = {}
period_starters = {}
time_elapsed_in_periods = 0
period_duration_in_minutes = 0

xt = [0] #ticks

# get starters for each period
for x in gb_data:
    if "NATIONAL BASKETBALL ASSOCIATION OFFICIAL PLAY-BY-PLAY" in x:
        capture = True
    elif "All Rights Reserved" in x:
        capture = False
    elif capture:
        
        if "Start of Period" in x:
            if len(xt)==4:
                time_elapsed_in_periods+=60*int(period_duration_in_minutes)
            pbp = True
            period_duration_in_minutes = int(x.split(":")[0])
            if gamestart:
                if len(xt)!=4:
                    time_elapsed_in_periods+=60*int(period_duration_in_minutes)
                xt.append(time_elapsed_in_periods)
                print(x,period_duration_in_minutes, time_elapsed_in_periods, len(xt))
            gamestart = True
            
            for t in period_starters:
                for p in period_starters[t]:
                    captured_data["players"][p].sub_in(time_elapsed_in_periods,plusminus)
            
            
        elif "End of " in x:
            for p in captured_data["players"]:
                if captured_data["players"][p].active:
                    captured_data["players"][p].sub_out(time_elapsed_in_periods+60*int(period_duration_in_minutes),plusminus)
            pbp = False
        elif pbp:
            datastr = x.split(" ") 
            time = timer_converter(datastr[0],time_elapsed_in_periods,period_duration_in_minutes*60)
            pbp_data = ' '.join(datastr[1:])
            parse_pbp(pbp_data,time)
        else:
            if "Starters" in x:
                d = x.split(" Starters: ")
                period_starters[d[0]] = d[1].split(' ')

game_end_time = time_elapsed_in_periods+60*int(period_duration_in_minutes)
xt.append(game_end_time)                
captured_data["pmlist"].append((game_end_time,plusminus))                    
for p in captured_data["players"]:
    captured_data["players"][p].check_stats()                


#graphing
def splitter(eventlist, aura):
    # print(eventlist)
    if len(eventlist)<=1:
        return eventlist
    newevents = [eventlist[0]]
    for i in range(1,len(eventlist)):
        if abs(newevents[-1][0]-eventlist[i][0])<=aura:
            x = newevents.pop()
            l = len(x[1])
            new_l = (l*x[0]+eventlist[i][0])/(l+1)
            newevents.append((new_l, x[1]+eventlist[i][1]))
        else:
            newevents.append(eventlist[i])
    # print(newevents)
    return newevents


middlepad = 5
offset = 0.15
fontsize = 15
plt.rcParams["figure.figsize"] = [32,20] 
fig, ax = plt.subplots()
ax.set_facecolor("#D9D9D9")
fig.set_facecolor("#12151C")
yt = []
ytl = []

player_amount = 0
visitor_amount = 0
for player in captured_data["players"]:
    player_amount+=1
    if captured_data["players"][player].is_visitor:
        visitor_amount+=1
        


row_no = 0
for player in captured_data["players"]:
    events = captured_data["players"][player].events
    is_vis = captured_data["players"][player].is_visitor
    # calculate row
    y_adjustment = row_no
    if is_vis:
        y_adjustment = visitor_amount-row_no
    else:
        y_adjustment = row_no+middlepad
    # add tick and label
    yt.append(y_adjustment+0.4)
    ytl.append(captured_data["players"][player].display_name)
    # write events
    shooting_events = []
    non_shooting_events = []
    for event in events:
        if event[1] in ['1','2','3','x','X','▽']:#,'A']:
            shooting_events.append(event)
        else:
            non_shooting_events.append(event)
    # print(player,3*len(xt))
    r = 5
    shooting_events = splitter(shooting_events,r*len(xt))
    
    non_shooting_events = splitter(non_shooting_events,r*len(xt))
    
    for event in shooting_events: #0.55, 0.2 offsets original
        plt.text(event[0],y_adjustment+0.55,event[1],fontsize=fontsize,horizontalalignment='center', verticalalignment='center')
    for event in non_shooting_events:
        plt.text(event[0],y_adjustment+0.2,event[1],fontsize=fontsize,horizontalalignment='center', verticalalignment='center')
    
    # create rectangles
    start_stints = captured_data["players"][player].start_stint
    end_stints = captured_data["players"][player].end_stint
    
    for i in range(len(captured_data["players"][player].start_stint)):
        pm = end_stints[i][1]-start_stints[i][1]
        length = end_stints[i][0]-start_stints[i][0]
        
        if (pm<0 and is_vis) or (pm>0 and not is_vis):
            colors = (1.0,(1.0-(min(abs(pm),30)/30)),(1.0-(min(abs(pm),30))/30))
        if (pm>0 and is_vis) or (pm<0 and not is_vis):
            colors = ((1.0-(min(abs(pm),30)/30)),1.0,(1.0-(min(abs(pm),30))/30))
        if pm==0:
            colors = (1.0,1.0,1.0)
        rect = plt.Rectangle((start_stints[i][0],y_adjustment),length,0.8, color=colors,ls="-")#,ec=(0,0,0))
        ax.add_patch(rect)
    
    row_no +=1

#plus minus
maxadv = 0
for x in captured_data["pmlist"]:
    if abs(x[1])>maxadv:
        maxadv=abs(x[1])
pml = []
for x in captured_data["pmlist"]:
    pml.append((x[0],3+visitor_amount-(1.5*x[1]/maxadv)))
for i in range(1,len(pml)):
    plt.plot([pml[i][0],pml[i-1][0]],[pml[i-1][1],pml[i-1][1]], color='black',linewidth=1)
    plt.plot([pml[i][0],pml[i][0]],[pml[i-1][1],pml[i][1]], color='black',linewidth=1)

#handle ticks

yt.append(4.5+visitor_amount)
yt.append(1.5+visitor_amount)
yt.append(3+visitor_amount)
ax.set_yticks(yt)
ytl.append(f"+{maxadv} {captured_data['home']['name_short'].capitalize()}")
ytl.append(f"+{maxadv} {captured_data['visitors']['name_short'].capitalize()}")
ytl.append(f"tie")
ax.tick_params(colors='white',labelsize=20 )
ax.set_yticklabels(ytl)

xtl = ['S']
i=1
while i<len(xt):
    if i<5:
        xtl.append(f'Q{i}')
    else:
        xtl.append(f'OT{i-4}')
    i+=1
ax.set_xticks(xt)
ax.set_xticklabels(xtl)

#lines
plt.axhline(4.5+visitor_amount, color='blue',linewidth=0.5)
plt.axhline(1.5+visitor_amount, color='blue',linewidth=0.5)
plt.axhline(3+visitor_amount, color='blue',linewidth=0.5)
for i in xt:
    plt.axvline(i,color='blue',linewidth=0.3)


plt.ylim((len(captured_data["players"])+middlepad,0.5))
plt.xlim((-30,game_end_time+30)) #used to be 10
plt.savefig("test.png")



#title
vis_name = captured_data["visitors"]["name_short"].capitalize()
home_name = captured_data["home"]["name_short"].capitalize()

while len(vis_name)!=len(home_name):
    if len(vis_name)<len(home_name):
        vis_name = ' '+vis_name
    else:
        home_name +=' '
title = f'{vis_name} {vis_score}-{home_score} {home_name}'

date = ' '.join(gb_data[2].split(" ")[1:4])

img = Image.open('test.png')
imgdraw = ImageDraw.Draw(img)
font = ImageFont.truetype("bahnschrift.ttf",70)
secondfont = ImageFont.truetype("bahnschrift.ttf",40)

titlelength = font.getlength(title)
datelength = secondfont.getlength(date)


imgdraw.text((1600-titlelength/2,100),title, font=font, fill=(255,255,255))
imgdraw.text((1600-datelength/2,175),date, font=secondfont, fill=(255,255,255))
img.save("test.png")

bg = Image.open("background.png")
data = Image.open("test.png")
fg = Image.open("en_overlay.png")

bg.paste(data, (0,0), data)
bg.paste(fg, (0,0), fg)
bg.save("final.png")

