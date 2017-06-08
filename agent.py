#!/usr/bin/env python

import threading
import time
import random

import sock
import sp_exceptions
import handler
from world_model import WorldModel

# nengo stuff
import numpy as np
import time
from numpy.linalg import svd, norm, pinv
import nengo
from numpy import pi

class Agent:
    def __init__(self):
        # whether we're connected to a server yet or not
        self.__connected = False

        # set all variables and important objects to appropriate values for
        # pre-connect state.

        # the socket used to communicate with the server
        self.__sock = None

        # models and the message handler for parsing and storing information
        self.wm = None
        self.msg_handler = None

        # parse thread and control variable
        self.__parsing = False
        self.__msg_thread = None

        self.__thinking = False # think thread and control variable
        self.__think_thread = None

        # whether we should run the think method
        self.__should_think_on_data = False

        # whether we should send commands
        self.__send_commands = False

        # adding goal post markers
        self.enemy_goal_pos = None
        self.own_goal_pos = None
        self.last_action = None
        self.last_balldir = None
        self.angle_to_goal = None

        self.decodes = self.init_turn_network()
        self.en_decodes = self.init_opp_network()

    def init_turn_network(self):
        # Use the following in your simulation
        T = 1.               # duration of simulation
        tau_ens_probe = .01  # Use this as the synapse parameter when creating Probes of Ensembles
        in_fun = lambda t: t # input function to your network
        N = 500  # Number of neurons in each Ensemble

        model = nengo.Network()
        with model:
            stim = nengo.Node(in_fun)
            ensA = nengo.Ensemble(N, dimensions=1)
            ensB = nengo.Ensemble(N, dimensions=1)
            
            nengo.Connection(stim, ensA)
            nengo.Connection(ensA, ensB, function=lambda x: 0.5*np.sin(pi*x))
            
            stim_p = nengo.Probe(stim)
            ensA_p = nengo.Probe(ensA, synapse=.01)
            ensB_p = nengo.Probe(ensB, synapse=.01)
            ensA_spikes_p = nengo.Probe(ensA.neurons, 'spikes')
            ensB_spikes_p = nengo.Probe(ensB.neurons, 'spikes')
        sim = nengo.Simulator(model, dt=.001)
        sim.run(T, progress_bar=False)
         
        decodes = sim.data[ensB_p]
        return decodes

    def init_opp_network(self):
        # Use the following in your simulation
        T = 1.               # duration of simulation
        tau_ens_probe = .01  # Use this as the synapse parameter when creating Probes of Ensembles
        in_fun = lambda t: t # input function to your network
        N = 500  # Number of neurons in each Ensemble

        model = nengo.Network()
        with model:
            stim = nengo.Node(in_fun)
            ensA = nengo.Ensemble(N, dimensions=1)
            ensB = nengo.Ensemble(N, dimensions=1)
            
            nengo.Connection(stim, ensA)
            nengo.Connection(ensA, ensB, function=lambda x: 0.5*np.sin(pi*x))
            
            stim_p = nengo.Probe(stim)
            ensA_p = nengo.Probe(ensA, synapse=.01)
            ensB_p = nengo.Probe(ensB, synapse=.01)
            ensA_spikes_p = nengo.Probe(ensA.neurons, 'spikes')
            ensB_spikes_p = nengo.Probe(ensB.neurons, 'spikes')
   
        sim = nengo.Simulator(model, dt=.001)
        sim.run(T, progress_bar=False)
         
        decodes = sim.data[ensB_p]
        return 0.5 - decodes

    def ball_to_turn(self, angle, decodes):
        ''' interpolate decodes to the correct value'''

        angle_idx =  int(angle*1000/360)
        return decodes[angle_idx]*360

    def connect(self, host, port, teamname, version=11):
        """
        Gives us a connection to the server as one player on a team.  This
        immediately connects the agent to the server and starts receiving and
        parsing the information it sends.
        """

        # if already connected, raise an error since user may have wanted to
        # connect again to a different server.
        if self.__connected:
            msg = "Cannot connect while already connected, disconnect first."
            raise sp_exceptions.AgentConnectionStateError(msg)

        # the pipe through which all of our communication takes place
        self.__sock = sock.Socket(host, port)

        # our models of the world and our body
        self.wm = WorldModel(handler.ActionHandler(self.__sock))

        # set the team name of the world model to the given name
        self.wm.teamname = teamname

        # handles all messages received from the server
        self.msg_handler = handler.MessageHandler(self.wm)

        # set up our threaded message receiving system
        self.__parsing = True # tell thread that we're currently running
        self.__msg_thread = threading.Thread(target=self.__message_loop,
                name="message_loop")
        self.__msg_thread.daemon = True # dies when parent thread dies

        # start processing received messages. this will catch the initial server
        # response and all subsequent communication.
        self.__msg_thread.start()

        # send the init message and allow the message handler to handle further
        # responses.
        init_address = self.__sock.address
        init_msg = "(init %s (version %d))"
        self.__sock.send(init_msg % (teamname, version))

        # wait until the socket receives a response from the server and gets its
        # assigned port.
        while self.__sock.address == init_address:
            time.sleep(0.0001)

        # create our thinking thread.  this will perform the actions necessary
        # to play a game of robo-soccer.
        self.__thinking = False
        self.__think_thread = threading.Thread(target=self.__think_loop,
                name="think_loop")
        self.__think_thread.daemon = True

        # set connected state.  done last to prevent state inconsistency if
        # something goes wrong beforehand.
        self.__connected = True

    def play(self):
        """
        Kicks off the thread that does the agent's thinking, allowing it to play
        during the game.  Throws an exception if called while the agent is
        already playing.
        """

        # ensure we're connected before doing anything
        if not self.__connected:
            msg = "Must be connected to a server to begin play."
            raise sp_exceptions.AgentConnectionStateError(msg)

        # throw exception if called while thread is already running
        if self.__thinking:
            raise sp_exceptions.AgentAlreadyPlayingError(
                "Agent is already playing.")

        # run the method that sets up the agent's persistant variables
        self.setup_environment()

        # tell the thread that it should be running, then start it
        self.__thinking = True
        self.__should_think_on_data = True
        self.__think_thread.start()

    def disconnect(self):
        """
        Tell the loop threads to stop and signal the server that we're
        disconnecting, then join the loop threads and destroy all our inner
        methods.

        Since the message loop thread can conceiveably block indefinitely while
        waiting for the server to respond, we only allow it (and the think loop
        for good measure) a short time to finish before simply giving up.

        Once an agent has been disconnected, it is 'dead' and cannot be used
        again.  All of its methods get replaced by a method that raises an
        exception every time it is called.
        """

        # don't do anything if not connected
        if not self.__connected:
            return

        # tell the loops to terminate
        self.__parsing = False
        self.__thinking = False

        # tell the server that we're quitting
        self.__sock.send("(bye)")

        # tell our threads to join, but only wait breifly for them to do so.
        # don't join them if they haven't been started (this can happen if
        # disconnect is called very quickly after connect).
        if self.__msg_thread.is_alive():
            self.__msg_thread.join(0.01)

        if self.__think_thread.is_alive():
            self.__think_thread.join(0.01)

        # reset all standard variables in this object.  self.__connected gets
        # reset here, along with all other non-user defined internal variables.
        Agent.__init__(self)

    def __message_loop(self):
        """
        Handles messages received from the server.

        This SHOULD NOT be called externally, since it's used as a threaded loop
        internally by this object.  Calling it externally is a BAD THING!
        """

        # loop until we're told to stop
        while self.__parsing:
            # receive message data from the server and pass it along to the
            # world model as-is.  the world model parses it and stores it within
            # itself for perusal at our leisure.
            raw_msg = self.__sock.recv()
            msg_type = self.msg_handler.handle_message(raw_msg)

            # we send commands all at once every cycle, ie. whenever a
            # 'sense_body' command is received
            if msg_type == handler.ActionHandler.CommandType.SENSE_BODY:
                self.__send_commands = True

            # flag new data as needing the think loop's attention
            self.__should_think_on_data = True

    def __think_loop(self):
        """
        Performs world model analysis and sends appropriate commands to the
        server to allow the agent to participate in the current game.

        Like the message loop, this SHOULD NOT be called externally.  Use the
        play method to start play, and the disconnect method to end it.
        """

        while self.__thinking:
            # tell the ActionHandler to send its enqueued messages if it is time
            if self.__send_commands:
                self.__send_commands = False
                self.wm.ah.send_commands()

            # only think if new data has arrived
            if self.__should_think_on_data:
                # flag that data has been processed.  this shouldn't be a race
                # condition, since the only change would be to make it True
                # before changing it to False again, and we're already going to
                # process data, so it doesn't make any difference.
                self.__should_think_on_data = False

                # performs the actions necessary for the agent to play soccer
                self.think()
            else:
                # prevent from burning up all the cpu time while waiting for data
                time.sleep(0.0001)

    def setup_environment(self):
        """
        Called before the think loop starts, this allows the user to store any
        variables/objects they'll want access to across subsequent calls to the
        think method.
        """

        self.in_kick_off_formation = False

    def think(self):
        """
        Performs a single step of thinking for our agent.  Gets called on every
        iteration of our think loop.
        """

        # DEBUG:  tells us if a thread dies
        if not self.__think_thread.is_alive() or not self.__msg_thread.is_alive():
            raise Exception("A thread died.")

        # take places on the field by uniform number
        if not self.in_kick_off_formation:

            # used to flip x coords for other side
            side_mod = 1
            if self.wm.side == WorldModel.SIDE_R:
                side_mod = -1

            if self.wm.uniform_number == 1:
                self.wm.teleport_to_point((-5 * side_mod, 30))
            elif self.wm.uniform_number == 2:
                self.wm.teleport_to_point((-40 * side_mod, 15))
            elif self.wm.uniform_number == 3:
                self.wm.teleport_to_point((-40 * side_mod, 00))
            elif self.wm.uniform_number == 4:
                self.wm.teleport_to_point((-40 * side_mod, -15))
            elif self.wm.uniform_number == 5:
                self.wm.teleport_to_point((-5 * side_mod, -30))
            elif self.wm.uniform_number == 6:
                self.wm.teleport_to_point((-20 * side_mod, 20))
            elif self.wm.uniform_number == 7:
                self.wm.teleport_to_point((-20 * side_mod, 0))
            elif self.wm.uniform_number == 8:
                self.wm.teleport_to_point((-20 * side_mod, -20))
            elif self.wm.uniform_number == 9:
                self.wm.teleport_to_point((-10 * side_mod, 0))
            elif self.wm.uniform_number == 10:
                self.wm.teleport_to_point((-10 * side_mod, 20))
            elif self.wm.uniform_number == 11:
                self.wm.teleport_to_point((-10 * side_mod, -20))

            self.in_kick_off_formation = True

            return

        # determine the enemy goal position
        goal_pos = None
        if self.wm.side == WorldModel.SIDE_R:
            goal_pos = (-55, 0)
        else:
            goal_pos = (55, 0)

        # kick off!
        if self.wm.is_before_kick_off():
            # player 9 takes the kick off
            if self.wm.uniform_number == 3:
                if self.wm.is_ball_kickable():
                    # kick with 100% extra effort at enemy goal
                    self.wm.kick_to(goal_pos, 1.0)
                else:
                    # move towards ball
                    if self.wm.ball is not None:
                        if (self.wm.ball.direction is not None and
                                -7 <= self.wm.ball.direction <= 7):
                            self.wm.ah.dash(50)
                        else:
                            self.wm.turn_body_to_point((0, 0))

                # turn to ball if we can see it, else face the enemy goal
                if self.wm.ball is not None:
                    self.wm.turn_neck_to_object(self.wm.ball)

                return
            else:
                pass
                return
        elif self.wm.is_dead_ball_us():
            if self.wm.uniform_number < 5:
                print('taking free kick')
                if self.wm.ball is not None and self.wm.abs_body_dir is not None:
                    self.kick_spot = self.wm.find_best_kick_spot(self.goal_pos, self.wm.get_object_absolute_coords(self.wm.ball))
                    if self.wm.euclidean_distance(self.wm.abs_coords, self.kick_spot) > self.wm.server_parameters.kickable_margin/2.0:
                        self.wm.ah.dash(65) # move toward kick spot
                        return

                    elif abs(self.wm.abs_body_dir - self.angle_to_goal) > 7:
                        self.wm.turn_body_to_point(self.enemy_goal_pos)

                    else: # all set, kick to goal
                        self.wm.kick_to(self.goal_pos, 1.0)
                else:
                    self.wm.ah.turn(30)
                return
            # elif self.playertype == 'off':
            else: 
                pass # do nothing for now
                print('waiting for free kick')
                return

        # attack!
        else:
            # find the ball
            if self.wm.ball is None or self.wm.ball.direction is None:
                self.wm.ah.turn(30)

                return

            # kick it at the enemy goal
            if self.wm.is_ball_kickable():
                goal_angle, goal_dist  = self.ball_to_turn(self.angle_to_goal, self.decodes), self.wm.get_distance_to_point(self.enemy_goal_pos)
                distances, angles = self.wm.get_enemies()
                enemy_angle = 0
                for d, a in zip(distances, angles):
                    enemy_angle += self.ball_to_turn(a, self.en_decodes)/d # weight angles by distance players are 
                kick_angle = .8*goal_angle + .2*enemy_angle

                self.wm.kick_to(self.wm.get_point(kick_angle, goal_dist), 1.0)
                # self.wm.kick_to(goal_pos, 1.0)
                return
            else:
                # move towards ball
                if -7 <= self.wm.ball.direction <= 7:
                    self.wm.ah.dash(65)
                else:
                    # face ball
                    # self.wm.ah.turn(self.wm.ball.direction / 2)
                    self.wm.ah.turn(self.ball_to_turn(self.wm.ball.direction, self.decodes))

                return


if __name__ == "__main__":
    import sys
    import multiprocessing as mp

    # enforce corrent number of arguments, print help otherwise
    if len(sys.argv) < 3:
        print "args: ./agent.py <team_name> <num_players>"
        sys.exit()

    def spawn_agent(team_name):
        """
        Used to run an agent in a seperate physical process.
        """

        a = Agent()
        a.connect("localhost", 6000, team_name)
        a.play()

        # we wait until we're killed
        while 1:
            # we sleep for a good while since we can only exit if terminated.
            time.sleep(1)

    # spawn all agents as seperate processes for maximum processing efficiency
    agentthreads = []
    for agent in xrange(min(11, int(sys.argv[2]))):
        print "  Spawning agent %d..." % agent

        at = mp.Process(target=spawn_agent, args=(sys.argv[1],))
        at.daemon = True
        at.start()

        agentthreads.append(at)

    print "Spawned %d agents." % len(agentthreads)
    print
    print "Playing soccer..."

    # wait until killed to terminate agent processes
    try:
        while 1:
            time.sleep(0.05)
    except KeyboardInterrupt:
        print
        print "Killing agent threads..."

        # terminate all agent processes
        count = 0
        for at in agentthreads:
            print "  Terminating agent %d..." % count
            at.terminate()
            count += 1
        print "Killed %d agent threads." % (count - 1)

        print
        print "Exiting."
        sys.exit()

