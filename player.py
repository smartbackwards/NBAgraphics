stat_order="FG FGA 3P 3PA FT FTA OR DR TOT A PF ST TO BS +/- PTS".split(" ")
class Player:
    def __init__(self, statstr, is_visitor):
        # assuming no one has a name that includes the singular letters G C and F
        stats = statstr.replace(" G "," ").replace(" C "," ").replace(" F "," ").split(" ")
        
        if ("DND" not in stats) and ("DNP" not in stats) and ("NWT" not in stats):
            self.status = "active"
            self.number = stats[0]
            self.name = ' '.join(stats[1:len(stats)-17])
            self.display_name = f'#{stats[0]} {stats[1][0]}.{" ".join(stats[2:len(stats)-17])}'
            self.pbp_name = stats[1][0]+"."+''.join(stats[2:len(stats)-17])
            self.minutes = stats[len(stats)-17]
            self.stats = []
            self.captured_stats = [0]*16
            self.is_visitor = is_visitor
            for i in range(len(stat_order)):
                self.stats.append(int(stats[len(stats)-16+i]))
        
            self.events = []
            self.start_stint = []
            self.end_stint = []
            self.active = False
                    
        else:
            self.status = "inactive"

    def sub_in(self,time,plusminus):
        if self.active:
            raise Exception(f"Trying to sub in active player {self.pbp_name} at {time}")
        else:
            self.active=True
            self.start_stint.append((time,plusminus))    
    
    def sub_out(self,time,plusminus):
        if not self.active:
            raise Exception(f"Trying to sub out inactive player {self.pbp_name} at {time}")
        else:
            self.active=False
            self.end_stint.append((time,plusminus))    
            
    def add_event(self,time,type):
        self.events.append((time,type))
    
    def add_to_captured_stats(self,categories):
        for c in categories:
            self.captured_stats[c]+=1
    
    def check_stats(self):
        # FG FGA 3P 3PA FT FTA OR DR TOT A PF ST TO BS +/- PTS       
        
        for event in self.events:
            if event[1]=='3':
                self.add_to_captured_stats([0,1,2,3,15,15,15]) #FG FGA 3P 3PA PTS*3
            elif event[1]=='▽':
                self.add_to_captured_stats([1,3]) #FGA 3PA
            elif event[1]=='2':
                self.add_to_captured_stats([0,1,15,15])
            elif event[1]=='X':
                self.add_to_captured_stats([1])
            elif event[1]=='1':
                self.add_to_captured_stats([4,5,15]) #FT FTA PTS
            elif event[1]=='x':
                self.add_to_captured_stats([5])
            elif event[1]=='O':
                self.add_to_captured_stats([6,8])
            elif event[1]=='D':
                self.add_to_captured_stats([7,8])
            elif event[1]=='A':
                self.add_to_captured_stats([9])
            elif event[1]=='F':
                self.add_to_captured_stats([10])
            elif event[1]=='S':
                self.add_to_captured_stats([11])
            elif event[1]=='↻':
                self.add_to_captured_stats([12])
            elif event[1]=='B':
                self.add_to_captured_stats([13])
        
        checkpm = 0    
        for i in range(len(self.start_stint)):
            if self.is_visitor:
                checkpm += self.end_stint[i][1]-self.start_stint[i][1]
            else:
                checkpm += self.start_stint[i][1]-self.end_stint[i][1]
        self.captured_stats[14] =checkpm
        
        for i in range(16):
            if i!=14 and self.captured_stats[i]!=self.stats[i]:
                raise Exception(f"wrong {stat_order[i]} for {self.name} ({self.captured_stats[i]} captured, {self.stats[i]} in box)")