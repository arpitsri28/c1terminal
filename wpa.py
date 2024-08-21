import gamelib
import random
import math
import warnings
from sys import maxsize
import json
import inspect

import gamelib.navigation


"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP, ATTACK_STATUS, ATTACK_EDGE, START_ATTACK
        global PREV_HEALTH, POST_ATTACK
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        ATTACK_STATUS = 0
        START_ATTACK = -1
        PREV_HEALTH = 30
        POST_ATTACK = 0
        # This is a good place to do initial setup
        self.scored_on_locations = []
        self.enemy_defenses_stats = []

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.
        game_map = gamelib.GameMap(self.config)
        self.starter_strategy(game_state, turn_state, game_map)
        #gamelib.debug_write(turn_state)
        game_state.submit_turn()


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """

    def starter_strategy(self, game_state, turn_string, game_map):
        """
        For defense we will use a spread out layout and some interceptors early on.
        We will place turrets near locations the opponent managed to score on.
        For offense we will use long range demolishers if they place stationary units near the enemy's front.
        If there are no stationary units to attack in the front, we will send Scouts to try and score quickly.
        """
        #START_ATTACK = 0
        global ATTACK_STATUS
        if game_state.turn_number % 2 == 1 and game_state.turn_number > 0 and game_state.turn_number < 10:
            ATTACK_STATUS = 1
        elif game_state.turn_number % 3 == 1 and game_state.turn_number >= 10:
            ATTACK_STATUS = 1
        else:
            ATTACK_STATUS = 0
        
        if ATTACK_STATUS == 0: 
            # First, place basic defenses
            self.build_defences(game_state, turn_string, intial_queue)
            
            self.build_defences(game_state, turn_string, priority_queue)

            self.build_reactive_defense(game_state)
            # Now build reactive defenses based on where the enemy scored
        elif ATTACK_STATUS == 1:
            my_empty_edges = self.filter_blocked_locations(my_edges, game_state)
            gamelib.debug_write("Deploy edges", my_empty_edges)
            path = self.least_damage_spawn_location(game_state, my_empty_edges)
            self.build_support(game_state, path)
            self.build_defences(game_state, turn_string, intial_queue)
    
            self.build_defences(game_state, turn_string, priority_queue)
            # Now build reactive defenses based on where the enemy scored
            self.build_reactive_defense(game_state)
            units_deployed, units_survived = self.attack(game_state, turn_string)
            # gamelib.debug_write("Units Deployed Actual", units_deployed)
            # gamelib.debug_write("Units Survived", units_survived) 
            
        # support_locations = [[11, 9], [17, 9], [7, 9], [21, 9]]
        # for i in support_locations:
        #     game_state.attempt_spawn(SUPPORT, i)
        #     game_state.attempt_upgrade(i)
        #     game_state.attempt_upgrade(i)
        
    def get_safe_edges(self, game_state):
        my_edges = [[0, 13], [1, 12], [2, 11], [3, 10], [4, 9], 
                        [5, 8], [6, 7], [7, 6], [8, 5], [9, 4], [10, 3], 
                        [11, 2], [12, 1], [13, 0], [27, 13], [26, 12], [25, 11], 
                        [24, 10], [23, 9], [22, 8], [21, 7], [20, 6], [19, 5], 
                        [18, 4], [17, 3], [16, 2], [15, 1], [14, 0]]
            
        my_empty_edges = self.filter_blocked_locations(my_edges, game_state)
        gamelib.debug_write("Deploy edges", my_empty_edges)

        enemy_hashmap = {(27, 14), (0, 14), (1, 15), (26, 15), 
                         (2, 16), (25, 16), (3, 17), (24, 17), 
                         (4, 18), (23, 18), (5, 19), (22, 19), 
                         (6, 20), (21, 20), (7, 21), (20, 21), 
                         (8, 22), (19, 22), (9, 23), (18, 23), 
                         (10, 24), (17, 24), (11, 25), (16, 25), 
                         (12, 26), (15, 26), (13, 27), (14, 27)}

        while my_empty_edges:
            paths = self.least_damage_spawn_path(game_state, my_empty_edges)
            gamelib.debug_write("Paths get safe", paths)
            if tuple(paths[-1]) in enemy_hashmap:
                break
            else:
                # Remove the start of the path with the least damage from empty edges
                my_empty_edges.remove(paths[0])
        
        return my_empty_edges
    
    def get_units_array(self, turn_string):
        state = json.loads(turn_string)
        units = state["p2Units"]
        unit_information = self.config["unitInformation"]  # Access unit configuration
        units_with_type = {}
        for i, unit_list in enumerate(units):  # Each i corresponds to a specific unit type
            unit_type = unit_information[i]["shorthand"]
            for unit in unit_list:
                x, y, health, unit_id = unit
                #units_with_type.append([x, y, health, unit_id, unit_type])
                if unit_type == 'FF':
                    units_with_type[(x, y)] = [health, "WALL"]
                    #gamelib.debug_write("Unit w/ Type", [x, y, health, unit_id, "WALL"])
                elif unit_type == 'DF':
                    units_with_type[(x, y)] = [health, "TURRET"]
                    #gamelib.debug_write("Unit w/ Type", [x, y, health, unit_id, "TURRET"])
                elif unit_type == 'EF':
                     units_with_type[(x, y)] = [health, "SUPPORT"]
                    #gamelib.debug_write("Unit w/ Type", [x, y, health, unit_id, "SUPPORT"])
        #gamelib.debug_write("Units dict", units_with_type)
        return units_with_type

    
    def determine_scout_target(self, game_state, scout_location):
        """
        Determines what a Scout will attack out of turrets, walls, and supports at a given location.

        Args:
            game_state: The current state of the game.
            scout_location: The current location of the Scout (e.g., [13, 0]).

        Returns:
            The target unit that the Scout will attack.
        """
        target = game_state.get_target(SCOUT)
        #gamelib.debug_write("Target Unit", target)
        
        if target:
            print(f"Scout at {scout_location} will attack: {target.unit_type} at {target.x, target.y}")
            gamelib.debug_write("Target unit", target)
            return (target.x,target.y)
        else:
            print(f"No target found for Scout at {scout_location}")
            return None, None


    def least_damage_spawn_path(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        damages = []
        paths = {}
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            #gamelib.debug_write("Path:", path)
            for path_location in path:
                # Get number of enemy turrets that can attack each location and multiply by turret damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
            damages.append(damage)
            paths[tuple(location)] = path
        
        # Now just return the location that takes the least damage
        least_spawn = location_options[damages.index(min(damages))]
        return paths[tuple(least_spawn)]

    def scouts_survived(self, game_state, num_of_units, turn_string, unit_spawn_location_options):
        scout_health = 12
        scout_damage = 2
        normal_turret_damage = 6
        upgraded_turret_damage = 14
        #start_location = self.least_damage_spawn_location(game_state, unit_spawn_location_options)
        #gamelib.debug_write("Start Location", start_location)
        paths = self.least_damage_spawn_path(game_state, unit_spawn_location_options)
        #gamelib.debug_write("Paths: ", paths)
        total_scout_health = num_of_units * scout_health
        destroyed_defenses = set()
        all_units = self.get_units_array(turn_string) #hashmap this
        #gamelib.debug_write("All units", all_units)
        for path in paths:
            scout = gamelib.GameUnit(SCOUT, self.config, player_index=0, health=scout_health, x=path[0], y=path[1])
            target_unit = game_state.get_target(scout)
            gamelib.debug_write("Target unit", target_unit)
            if target_unit:
                target = (target_unit.x, target_unit.y)
                if target in all_units:
                    if target in destroyed_defenses:
                        continue
                    unit_desc = all_units[target]
                    unit_desc[0] -= (num_of_units * scout_damage)
                    if unit_desc[0] <= 0:
                        destroyed_defenses.add(target)
            #how much damage the defenses do to our scouts before they reach the end
            attackers = game_state.get_attackers(path, 0)
            #grouped_attackers = self.group_attackers(attackers)
            gamelib.debug_write("Attackers", attackers)
            for attacker in attackers:
                gamelib.debug_write("Current Attacker", attacker)
                if attacker.unit_type == 'DF':
                    if attacker.upgrade:
                        total_scout_health -= upgraded_turret_damage
                    else:
                        total_scout_health -= normal_turret_damage
                    gamelib.debug_write("Scout Health Loop", total_scout_health)
                    num_of_units = math.ceil(total_scout_health / scout_health)
        
        gamelib.debug_write("Total scout health", total_scout_health)
        scouts_survived = max(num_of_units, 0)
        gamelib.debug_write("Scouts survived", scouts_survived)  
        num_of_defenses = len(destroyed_defenses)
        return scouts_survived, num_of_defenses

    def demolishers_survived(self, game_state, num_of_units, turn_string, unit_spawn_location_options):
        demolisher_health = 5
        demolisher_damage = 8
        normal_turret_damage = 6
        upgraded_turret_damage = 14
        # start_location = self.least_damage_spawn_location(game_state, unit_spawn_location_options)
        # gamelib.debug_write("Start Location", start_location)
        # paths = game_state.find_path_to_edge(start_location, None)
        paths = self.least_damage_spawn_path(game_state, unit_spawn_location_options)
        #gamelib.debug_write("Paths: ", paths)
        total_demolisher_health = num_of_units * demolisher_health
        destroyed_defenses = set()
        all_units = self.get_units_array(turn_string) #hashmap this
        #gamelib.debug_write("All units", all_units)
        #gamelib.debug_write("All units", all_units)
        for path in paths:
            #how much damage a scout does on the defenses and updates the health of each defense in the list
            #range_path = game_map.get_locations_in_range(path, scout_range) #don't need this cuz directly target get
            #gamelib.debug_write("Range Paths: ", range_path)
            #stationary_units = self.stationary_units_in_range(game_state, all_units, range_path) same same
            #gamelib.debug_write("Stationary in Range: ", stationary_units)
            demolisher = gamelib.GameUnit(DEMOLISHER, self.config, player_index=0, health=demolisher_health, x=path[0], y=path[1])

            target_unit = game_state.get_target(demolisher)
            gamelib.debug_write("Target unit", target_unit)
            if target_unit:
                target = (target_unit.x, target_unit.y)
                if target in all_units:
                    if target in destroyed_defenses:
                        continue
                    unit_desc = all_units[target]
                    unit_desc[0] -= (num_of_units * demolisher_damage * 2)
                    if unit_desc[0] <= 0:
                        destroyed_defenses.add(target)
            #how much damage the defenses do to our scouts before they reach the end
            attackers = game_state.get_attackers(path, 0)
            #grouped_attackers = self.group_attackers(attackers)
            gamelib.debug_write("Attackers", attackers)
            for attacker in attackers:
                gamelib.debug_write("Current Attacker", attacker)
                if attacker.unit_type == 'DF':
                    if attacker.upgrade:
                        total_demolisher_health -= upgraded_turret_damage
                    else:
                        total_demolisher_health -= normal_turret_damage
                    gamelib.debug_write("Demolisher Health Loop", total_demolisher_health)
                    num_of_units = math.ceil(total_demolisher_health / demolisher_health)
        
        gamelib.debug_write("Total demolisher health", total_demolisher_health)
        scouts_survived = max(num_of_units, 0)
        gamelib.debug_write("Demolishers survived", scouts_survived)  
        num_of_defenses = len(destroyed_defenses)
        return scouts_survived, num_of_defenses                              

    def freq(self, units_deployed, units_survived):
        global START_ATTACK
        upper_survival_threshold = 0.7
        percentage_survived = units_survived/units_deployed
        if percentage_survived >= upper_survival_threshold:
            return START_ATTACK + 2
        else:
            return START_ATTACK + 3

    def attack(self, game_state, turn_string):
        my_empty_edges = self.filter_blocked_locations(my_edges, game_state)
        path = self.least_damage_spawn_location(game_state, my_empty_edges)
        num_units = int(game_state.get_resource(MP))
        gamelib.debug_write("Scouts deployed", num_units)
        # num_units_d = math.ceil(num_units / 3)
        # gamelib.debug_write("Demolishers deployed", num_units_d)
        scout_survived, def_dest_scout = self.scouts_survived(game_state, num_units, turn_string, my_empty_edges)
        # demolisher_survived, def_dest_dem = self.demolishers_survived(game_state, num_units_d, turn_string, my_empty_edges)
        # demolisher_survived = demolisher_survived * 2
        # if scout_survived > demolisher_survived:
        #     game_state.attempt_spawn(SCOUT, path, 1000)
        #     unit_deployed = num_units
        # elif demolisher_survived > scout_survived:
        #     game_state.attempt_spawn(DEMOLISHER, path, 1000)
        #     unit_deployed = num_units_d
        # else:
        #     if def_dest_scout >= def_dest_dem:
        #         game_state.attempt_spawn(SCOUT, path, 1000)
        #         unit_deployed = num_units
        #     else:
        #         game_state.attempt_spawn(DEMOLISHER, path, 1000)
        #         unit_deployed = num_units_d
        game_state.attempt_spawn(SCOUT, path, 1000)
        unit_deployed = num_units
        return unit_deployed, scout_survived


    def get_our_units_array(self, turn_string):
        state = json.loads(turn_string)
        units = state["p1Units"]
        unit_information = self.config["unitInformation"]  # Access unit configuration
        units_with_type = {}
        for i, unit_list in enumerate(units):  # Each i corresponds to a specific unit type
            unit_type = unit_information[i]["shorthand"]
            for unit in unit_list:
                x, y, health, unit_id = unit
                #units_with_type.append([x, y, health, unit_id, unit_type])
                if unit_type == 'FF':
                    units_with_type[(x, y)] = [health, "WALL"]
                    #gamelib.debug_write("Unit w/ Type", [x, y, health, unit_id, "WALL"])
                elif unit_type == 'DF':
                    units_with_type[(x, y)] = [health, "TURRET"]
                    #gamelib.debug_write("Unit w/ Type", [x, y, health, unit_id, "TURRET"])
                elif unit_type == 'EF':
                     units_with_type[(x, y)] = [health, "SUPPORT"]
                    #gamelib.debug_write("Unit w/ Type", [x, y, health, unit_id, "SUPPORT"])
        gamelib.debug_write("Units dict", units_with_type)
        return units_with_type
    
    def defense_scouts(self, game_state, game_map, num_of_units, all_units, paths):
        scout_range = 4.5
        scout_health = 12
        scout_damage = 2
        normal_turret_damage = 6
        upgraded_turret_damage = 14
        total_scout_health = num_of_units * scout_health
        destroyed_defenses = set()
        #gamelib.debug_write("All units", all_units)
        for path in paths:
            scout = gamelib.GameUnit(SCOUT, self.config, player_index=0, health=scout_health, x=path[0], y=path[1])
            target_unit = game_state.get_target(scout)
            #gamelib.debug_write("Target unit", target_unit)
            if target_unit:
                target = (target_unit.x, target_unit.y)
                if target in all_units:
                    if target in destroyed_defenses:
                        continue
                    unit_desc = all_units[target]
                    unit_desc[0] -= (num_of_units * scout_damage)
                    if unit_desc[0] <= 0:
                        destroyed_defenses.add(target)
            #how much damage the defenses do to our scouts before they reach the end
            attackers = game_state.get_attackers(path, 0)
            #grouped_attackers = self.group_attackers(attackers)
            #gamelib.debug_write("Attackers", attackers)
            for attacker in attackers:
                #gamelib.debug_write("Current Attacker", attacker)
                if attacker.unit_type == 'DF':
                    total_scout_health -= 14
                    #gamelib.debug_write("Scout Health Loop", total_scout_health)
                    num_of_units = math.ceil(total_scout_health / scout_health)
        
        #gamelib.debug_write("Total scout health", total_scout_health)
        scouts_survived = max(num_of_units, 0)
        #gamelib.debug_write("Scouts survived", scouts_survived)  
        return scouts_survived

    def build_scout_defense(self, game_state, game_map, turn_string):
        enemy_edges = [[13, 27], [14, 27], [11, 25], [16, 25], [9, 23], 
                       [18, 23], [8, 22], [19, 22], [6, 20], [21, 20], 
                       [5, 19], [22, 19], [3, 17], [24, 17], [2, 16], 
                       [25, 16], [0, 14], [27, 14]]
        enemy_empty_edges = self.filter_blocked_locations(enemy_edges, game_state)
        paths = self.least_damage_spawn_path(game_state, enemy_empty_edges)
        end_location = paths[-1]
        gamelib.debug_write("Predicted scored on", end_location)
        sim_range = game_map.get_locations_in_range(end_location, 7)
        n = 15
        turret_health = 75
        if len(sim_range) >= n:
            random_turret_locations = random.sample(sim_range, n)
        else:
            # If there are fewer than n locations available, just use all of them
            random_turret_locations = sim_range
        #gamelib.debug_write("Sim Range", sim_range)
        num_units = game_state.get_resource(MP, 1)
        sim_survived = []
        all_units = self.get_units_array(turn_string)
        for i in sim_range:
            all_units_temp = all_units
            all_units_temp[tuple(i)] = [turret_health, "TURRET"]
            num_survived = self.defense_scouts(game_state, game_map, num_units, all_units_temp, paths)
            sim_survived.append(num_survived)
        #gamelib.debug_write("Sim Survived", sim_survived)
        return sim_range[sim_survived.index(min(sim_survived))]


    #need to increase length of priority_queue
    global intial_queue, priority_queue
    support_locations = [[11, 9], [17, 9], [7, 9], [21, 9]]
    intial_queue = [[[4, 12], 'TURRET'], [[4, 12], 'UPGRADE'], [[10, 12], 'TURRET'],
                    [[10, 12], 'UPGRADE'], [[17, 12], 'TURRET'], [[17, 12], 'UPGRADE'],
                    [[23, 12], 'TURRET'], [[23, 12], 'UPGRADE'], [[4, 13], 'WALL'], 
                    [[4, 13], 'UPGRADE'], [[23, 13], 'WALL'], [[23, 13], 'UPGRADE'],
                      ]
    priority_queue = [[[10, 13], 'WALL'], [[10, 13], 'UPGRADE'], 
                      [[17, 13], 'WALL'], [[17, 13], 'UPGRADE'],
                      [[24, 12], 'TURRET'], [[24, 13], 'WALL'],
                      [[24, 12], 'UPGRADE'], 
                      [[3, 12], 'TURRET'], [[3, 13], 'WALL'], 
                      [[3, 12], 'UPGRADE'],
                      [[16, 12], 'TURRET'], [[11, 12], 'TURRET'],
                      [[16, 12], 'UPGRADE'], [[11, 12], 'UPGRADE'], 
                      [[16, 13], 'WALL'], [[11, 13], 'WALL'],
                      [[16, 13], 'UPGRADE'], [[11, 13], 'UPGRADE'], 
                      [[24, 13], 'UPGRADE'], [[3, 13], 'UPGRADE'],
                      [[18, 12], 'TURRET'], [[25, 12], 'TURRET'], 
                      [[18, 13], 'WALL'], [[25, 12], 'UPGRADE'], 
                      [[2, 12], 'TURRET'], [[9, 12], 'TURRET'], 
                      [[2, 13], 'WALL'], [[9, 13], 'WALL'],
                      [[2, 12], 'UPGRADE'], [[9, 12], 'UPGRADE'], 
                      [[2, 13], 'UPGRADE'], [[9, 13], 'UPGRADE'],
                      ]
    
    '''
    [[0,13], 'WALL'], [[1,13], 'WALL'], 
    [[27,13], 'WALL'], [[26,13], 'WALL'],[[2,13], 'WALL'], [[25,13], 'WALL'],
    [[0,13], 'UPGRADE'], [[1,13], 'UPGRADE'], [[27,13], 'UPGRADE'], [[26,13], 'UPGRADE']
    '''
                        
    
    global bottom_left_edge, bottom_right_edge, left_top, quad_1, quad_2, quad_3, quad_4 # quad_3 refers to bottom_right
    bottom_left_edge = {(7, 6), (0, 13), (2, 11), (6, 7), (4, 9), 
                        (5, 8), (3, 10), (10, 3), (11, 2), (1, 12), 
                        (8, 5), (12, 1), (9, 4), (13, 0)}
    quad_1 = [[0, 13], [1, 12], [2, 11], [3, 10], [4, 9], [5, 8], [6, 7]]
    quad_2 = [[7, 6], [8, 5], [9, 4], [10, 3], [11, 2], [12, 1], [13, 0]]
    quad_3 = [[20, 6], [19, 5], [18, 4], [17, 3], [16, 2], [15, 1], [14, 0]]
    quad_4 = [[27, 13], [26, 12], [25, 11], [24, 10], [23, 9], [22, 8], [21, 7]]
              
    
    bottom_right_edge = {(15, 1), (20, 6), (24, 10), (14, 0), (27, 13), 
                            (25, 11), (22, 8), (21, 7), (18, 4), (26, 12), 
                            (19, 5), (17, 3), (23, 9), (16, 2)}
    def build_support(self, game_state, spawn_location):
        if spawn_location in quad_1:
            game_state.attempt_spawn(SUPPORT, [spawn_location[0] + 1, spawn_location[1] - 1])
            if game_state.get_resource(SP) > 12:
                game_state.attempt_upgrade([spawn_location[0] + 1, spawn_location[1] - 1])
            game_state.attempt_remove([spawn_location[0] + 1, spawn_location[1] - 1])
        elif spawn_location in quad_2:
            game_state.attempt_spawn(SUPPORT, [spawn_location[0] + 1, spawn_location[1]])
            if game_state.get_resource(SP) > 12:
                game_state.attempt_upgrade([spawn_location[0] + 1, spawn_location[1]])
            game_state.attempt_remove([spawn_location[0] + 1, spawn_location[1]])
        elif spawn_location in quad_3:
            game_state.attempt_spawn(SUPPORT, [spawn_location[0] - 1, spawn_location[1]])
            if game_state.get_resource(SP) > 12:
                game_state.attempt_upgrade([spawn_location[0] - 1, spawn_location[1]])
            game_state.attempt_remove([spawn_location[0] - 1, spawn_location[1]])
        elif spawn_location in quad_4:
            game_state.attempt_spawn(SUPPORT, [spawn_location[0] - 1, spawn_location[1] - 1])
            if game_state.get_resource(SP) > 12:
                game_state.attempt_upgrade([spawn_location[0] - 1, spawn_location[1] - 1])
            game_state.attempt_remove([spawn_location[0] - 1, spawn_location[1] - 1])



    
    global my_edges
    '''
    my_edges = [[8, 5], [9, 4], [10, 3], 
                [11, 2], [12, 1], [13, 0], [19, 5], [18, 4], [17, 3], 
                [16, 2], [15, 1], [14, 0]]
    '''
    
    my_edges = [[0, 13], [1, 12], [2, 11], [3, 10], [4, 9], 
                        [5, 8], [6, 7], [7, 6], [8, 5], [9, 4], [10, 3], 
                        [11, 2], [12, 1], [13, 0], [27, 13], [26, 12], [25, 11], 
                        [24, 10], [23, 9], [22, 8], [21, 7], [20, 6], [19, 5], 
                        [18, 4], [17, 3], [16, 2], [15, 1], [14, 0]]
    
    def build_defences(self, game_state, turn_string, defence_list):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy demolishers can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        for i in defence_list:
            if i[1] == "WALL":
                game_state.attempt_spawn(WALL, i[0])
            elif i[1] == "TURRET":
                game_state.attempt_spawn(TURRET, i[0])
            elif i[1] == "SUPPORT":
                game_state.attempt_spawn(SUPPORT, i[0])
            elif i[1] == "UPGRADE":
                game_state.attempt_upgrade(i[0])
        

    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """
        for location in self.scored_on_locations:
            # Build turret one space above so that it doesn't block our own edge spawn locations
            if tuple(location) in bottom_left_edge:
                build_location = [location[0] + 1, location[1] - 1]
                game_state.attempt_spawn(TURRET, build_location)
            else:
                build_location = [location[0] - 1, location[1] - 1]
                game_state.attempt_spawn(TURRET, build_location)

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location, game_state.get_target_edge(location))
            damage = 0
            #gamelib.debug_write("Path:", path)
            for path_location in path:
                # Get number of enemy turrets that can attack each location and multiply by turret damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
            damages.append(damage)
        
        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]
    
    def least_damage_spawn_path(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        damages = []
        paths = {}
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            #gamelib.debug_write("Path:", path)
            for path_location in path:
                # Get number of enemy turrets that can attack each location and multiply by turret damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
            damages.append(damage)
            paths[tuple(location)] = path
        
        # Now just return the location that takes the least damage
        least_spawn = location_options[damages.index(min(damages))]
        return paths[tuple(least_spawn)]

    def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units
        
    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))
    
    
if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
