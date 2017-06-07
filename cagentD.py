import random
# from soccerpy.agent import Agent as baseAgent
from world_model import WorldModel
from cagent_main import Agent


class AgentD(Agent):
    """
    The extended Agent class with specific heuritics
    """
    def __init__(self):
        super(AgentD, self).__init__('def')
    def decisionLoop(self):
        try:
            return self.defaultaction()
            #if self.find_ball(): 
            #    if self.wm.get_distance_to_point(self.own_goal_pos) > 15:
            #        # print "overstepping"
            #        self.wm.turn_body_to_point(self.own_goal_pos)
            #        self.wm.ah.dash(70)
            #        return
            #    # if should shoot, full power
            #    # if self.shall_shoot():
            #        # return self.shoot()
            #    # else shd pass to closest teammate
            #    elif self.shall_pass():
            #        return self.passes()
            #    # else shd dribble
            #    # elif self.shall_dribble():
            #        # return self.dribble()
            #    elif self.shall_move_to_ball():
            #        return self.move_to_ball()
            #    elif self.shall_move_to_defend():
            #        return self.move_to_defend()
            #    # elif self.shall_move_to_enemy_goalpos():
            #        # return self.move_to_enemy_goalpos()
            #    else:
            #        return self.defaultaction()
            #else:
            #    print('D couldnt find ball')
            #    return self.defaultaction()
        except Exception as inst:
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to be printed directly
            print "exceptions thrown, using fallback"
            self.defaultaction()

