import random
# from soccerpy.agent import Agent as baseAgent
from soccerpy.world_model import WorldModel
from cagent_main import Agent


class AgentO(Agent):
    """
    The extended Agent class with specific heuritics
    """
    def __init__(self):
        super(AgentO, self).__init__('off')

    def decisionLoop(self):
        try:
            return self.defaultaction()
            #if self.wm.ball is None or self.wm.ball.direction is None:
            #    print('finding ball')
            #    self.find_ball()
            #    # if should shoot, full power
            #if self.shall_shoot():
            #    print('shooting')
            #    return self.shoot()
            ## else shd pass to closest teammate
            #elif self.shall_pass():
            #    print('passing')
            #    return self.passes()
            ## else shd dribble
            #elif self.shall_dribble():
            #    print('dribbling')
            #    return self.dribble()
            #elif self.shall_move_to_ball():
            #    print('moving to ball')
            #    return self.move_to_ball()
            #elif self.shall_move_to_defend():
            #    print('moving to defend')
            #    return self.move_to_defend()
            #elif self.shall_move_to_enemy_goalpos():
            #    print('moving to enemy goal')
            #    return self.move_to_enemy_goalpos()
            #else:
            #    print('using default')
            #    return self.defaultaction()
        except Exception as inst:
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to be printed directly
            print "exceptions thrown, using fallback"
            self.defaultaction()


# by role: striker, defender
# do the same preconds, but def on role diff actions
# 1. 
# shoot:
# close enuf to ball and to self.enemy_goal_pos
# if self.wm.ball.distance < 10 and self.get_distance_to_point(self.enemy_goal_pos) < 20 and self.is_ball_kickable():



# shoot
# pass
# move

# striker:
# 

# strategy: ordered
# 1. close to ball: grab, carry toward goal, pass or shoot
# 2. ain't, move to enemy (if enemy has ball), goal (if we have ball n jersey num), ball (if enemy n closest, or jersey num)
# 3. 

# conditions shd be:
# shoot: ball aint none, ball kickable, close to goalpos


# Enum fields
# self.get_distance_to_point(self.enemy_goal_pos)
# self.get_angle_to_point(self.enemy_goal_pos)
# self.wm.ball.distance
# self.wm.ball.direction
# p = self.get_nearest_teammate()
# p.distance
# p.direction
# q = self.get_neatest_enemy()
# q.distance
# q.direction
# self.is_ball_owned_by_us
# self.is_ball_owned_by_enemy
# self.is_ball_kickable

# actions and their triggers
# shoot
# pass
# move

# print dir(WorldModel(''))
# print dir(Agent())

# va = 1
# print None or va[0]
# print random.randrange(-30,30)

