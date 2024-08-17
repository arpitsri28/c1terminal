import gamelib
import random
import math
import warnings
from sys import maxsize
import json

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
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP, ATTACK_STATUS
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
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

        if game_state.turn_number % 3 == 0 and game_state.turn_number > 0:
            ATTACK_STATUS = 1
        else:
            ATTACK_STATUS = 0
        
        if ATTACK_STATUS == 0:
            # First, place basic defenses
            self.build_defences(game_state)
            # Now build reactive defenses based on where the enemy scored
            self.build_reactive_defense(game_state)
        elif ATTACK_STATUS == 1:
            my_edges = [[0, 13], [1, 12], [2, 11], [3, 10], [4, 9], 
                        [5, 8], [6, 7], [7, 6], [8, 5], [9, 4], [10, 3], 
                        [11, 2], [12, 1], [13, 0], [27, 13], [26, 12], [25, 11], 
                        [24, 10], [23, 9], [22, 8], [21, 7], [20, 6], [19, 5], 
                        [18, 4], [17, 3], [16, 2], [15, 1], [14, 0]]
            
            my_empty_edges = self.filter_blocked_locations(my_edges, game_state)
            path = self.least_damage_spawn_location(game_state, my_empty_edges)
            self.build_support(game_state, game_state.get_target_edge(path))
            self.build_defences(game_state)
            # Now build reactive defenses based on where the enemy scored
            self.build_reactive_defense(game_state)
            game_state.attempt_spawn(SCOUT, path, 1000)

        # If the turn is less than 5, stall with interceptors and wait to see enemy's base
        #if game_state.turn_number < 5:
            #self.stall_with_interceptors(game_state)
        else:
            # Now let's analyze the enemy base to see where their defenses are concentrated.
            # If they have many units in the front we can build a line for our demolishers to attack them at long range.
            # if self.detect_enemy_unit(game_state, unit_type=None, valid_x=None, valid_y=[14, 15]) > 10:
            #     self.demolisher_line_strategy(game_state)
            # else:
                # They don't have many units in the front so lets figure out their least defended area and send Scouts there.

                # Only spawn Scouts every other turn
                # Sending more at once is better since attacks can only hit a single scout at a time
                if game_state.turn_number % 3 == 0 and game_state.turn_number > 0:
                    # To simplify we will just check sending them from back left and right
                    self.corner_attack(game_state)

                # Lastly, if we have spare SP, let's build some supports
                support_locations = [[13, 2], [14, 2], [13, 3], [14, 3]]
                game_state.attempt_spawn(SUPPORT, support_locations)

        
        support_locations = [[13, 2], [14, 2], [13, 3], [14, 3]]
        game_state.attempt_spawn(SUPPORT, support_locations)
              
    
    def get_enemy_defenses_in_range(self, game_state, locations):
        """
        Returns the locations of enemy support, turrets, and walls within the given locations.

        Args:
            game_state: The current state of the game.
            locations: A list of locations to check for enemy defenses.

        Returns:
            A tuple containing lists of turret locations, wall locations, and support locations within the specified locations.
        """
        enemy_defenses = []
    
        for location in locations:
            stationary_unit = game_state.contains_stationary_unit(location)
            if stationary_unit == TURRET:
                enemy_defenses.append([TURRET, location])
            elif stationary_unit == WALL:
                enemy_defenses.append([WALL, location])
            elif stationary_unit == SUPPORT:
                enemy_defenses.append([SUPPORT, location])

        return enemy_defenses

    # def get_units_array(self, turn_string):
    #     state = json.loads(turn_string)
    #     p2_units = state["p2Units"]
    #     #Flattening the list to get all units as a single list
    #     flat_p2_units = [item for sublist in p2_units for item in sublist]
    #     gamelib.debug_write("Units array", flat_p2_units)
    #     return flat_p2_units
    
    def get_units_array(self, turn_string):
        state = json.loads(turn_string)
        units = state["p2Units"]
        unit_information = self.config["unitInformation"]  # Access unit configuration
        units_with_type = []
        for i, unit_list in enumerate(units):  # Each i corresponds to a specific unit type
            unit_type = unit_information[i]["shorthand"]
            for unit in unit_list:
                x, y, health, unit_id = unit
                #units_with_type.append([x, y, health, unit_id, unit_type])
                if unit_type == 'FF':
                    units_with_type.append([x, y, health, unit_id, "WALL"])
                    #gamelib.debug_write("Unit w/ Type", [x, y, health, unit_id, "WALL"])
                elif unit_type == 'DF':
                    units_with_type.append([x, y, health, unit_id, "TURRET"])
                    #gamelib.debug_write("Unit w/ Type", [x, y, health, unit_id, "TURRET"])
                elif unit_type == 'EF':
                    units_with_type.append([x, y, health, unit_id, "SUPPORT"])
                    #gamelib.debug_write("Unit w/ Type", [x, y, health, unit_id, "SUPPORT"])
                
        return units_with_type
    
    def stationary_units_in_range(self, game_state, units, locations):
        """
        Gives an array of stationary units within a specific range of locations.
        Each element of the array is in the format [x, y, health, id, type].

        Args: 
        game_state: A GameState object representing the gamestate we want to traverse.
        units: Array of units obtained from the turn string.
        locations: List of locations to filter the stationary units by.

        Returns:
        List of stationary units within the given range of locations.
        """
        stationary_units = []
        
        for unit in units:
            if [unit[0], unit[1]] in locations:
                stationary_units.append(unit)
                #unit_location =   # Get the location as a list [x, y]
                #gamelib.debug_write("Units desc", unit_type)
        return stationary_units

    def determine_scout_target(self, game_state, scout_location):
        """
        Determines what a Scout will attack out of turrets, walls, and supports at a given location.

        Args:
            game_state: The current state of the game.
            scout_location: The current location of the Scout (e.g., [13, 0]).

        Returns:
            The target unit that the Scout will attack.
        """
        scout = gamelib.GameUnit(SCOUT, game_state.config, player_index=0, health=12, x=scout_location[0], y=scout_location[1])

        target = game_state.get_target(scout)
        
        if target:
            print(f"Scout at {scout_location} will attack: {target.unit_type} at {target.x, target.y}")
            return target.unit_type, (target.x, target.y)
        else:
            print(f"No target found for Scout at {scout_location}")
            return None, None


    def scouts_survived(self, game_state, game_map, num_of_units, turn_string, unit_spawn_location_options):
        scout_range = 4.5
        scout_health = 12
        scout_damage = 2
        start_location = self.least_damage_spawn_location(game_state, unit_spawn_location_options)
        gamelib.debug_write("Start Location", start_location)
        paths = game_state.find_path_to_edge(start_location, None)
        #gamelib.debug_write("Paths: ", paths)
        total_scout_health = num_of_units * scout_health
        destroyed_defenses = []
        all_units = self.get_units_array(turn_string)
        #gamelib.debug_write("All units", all_units)
        #gamelib.debug_write("All units", all_units)
        for path in paths:
            #how much damage a scout does on the defenses and updates the health of each defense in the list
            range_path = game_map.get_locations_in_range(path, scout_range)
            #gamelib.debug_write("Range Paths: ", range_path)
            stationary_units = self.stationary_units_in_range(game_state, all_units, range_path)
            gamelib.debug_write("Stationary in Range: ", stationary_units)
            target_unit_type, target_location = self.determine_scout_target(game_state, path)
            for defense in stationary_units:
                unit_type = defense[-1]
                location = [defense[0], defense[1]]
                if [unit_type, location] in destroyed_defenses:
                    continue
                if target_unit_type == unit_type and target_location == location:
                    defense[2] = defense[2] - (num_of_units * scout_damage)
                    if defense[2] <= 0:
                        destroyed_defenses.append([unit_type, location])
            #how much damage the defenses do to our scouts before they reach the end
            attackers = game_state.get_attackers(path, 0)
            #grouped_attackers = self.group_attackers(attackers)
            gamelib.debug_write("Attackers", attackers)
            for attacker in attackers:
                # Extract unit type from the string
                #unit_type = 
                if attacker.unit_type == 'DF':
                    total_scout_health -= 6
                #gamelib.debug_write("Attacker",type(attacker))
        if total_scout_health < 6:
            scouts_survived = 0
        else:
            gamelib.debug_write("Total scout health", total_scout_health)
            scouts_survived = max(total_scout_health // scout_health, 0) 
        gamelib.debug_write("Scouts survived", scouts_survived)  
        return scouts_survived
    
    def optimal_scout_attack(self, game_state, turn_string):
        
        unit_spawn_location_options = [[0, 13], [1, 12], [2, 11], [3, 10], [4, 9], 
                        [5, 8], [6, 7], [7, 6], [8, 5], [9, 4], [10, 3], 
                        [11, 2], [12, 1], [13, 0], [27, 13], [26, 12], [25, 11], 
                        [24, 10], [23, 9], [22, 8], [21, 7], [20, 6], [19, 5], 
                        [18, 4], [17, 3], [16, 2], [15, 1], [14, 0]]

        
        #my_edges = [[13,0], [14,0]]
            
        #unit_spawn_location_options = self.filter_blocked_locations(my_edges, game_state)
        #gamelib.debug_write(unit_spawn_location_options)
        num_of_units = int(game_state.get_resource(MP))

        scouts_survived, location = self.scouts_survived(game_state, game_state.game_map, num_of_units, turn_string, unit_spawn_location_options)

        gamelib.debug_write("Scouts survived", scouts_survived)
        return location

    def group_attackers(attackers, group_size=5):
        grouped_attackers = []
        for i in range(0, len(attackers), group_size):
            group = attackers[i:i + group_size]
            processed_group = [attacker.split(", ") for attacker in group]
            grouped_attackers.append(processed_group)
        return grouped_attackers

    def corner_attack(self, game_state):
        scout_spawn_location_options = [[13, 0], [14, 0]]
        best_location = self.least_damage_spawn_location(game_state, scout_spawn_location_options)
        game_state.attempt_spawn(SCOUT, best_location, 1000)

    #need to increase length of priority_queue
    global priority_queue
    priority_queue = [[[5, 13], 'TURRET'], [[5, 13], 'UPGRADE'], [[14, 13], 'TURRET'], [[14, 13], 'UPGRADE'],
                        [[23, 13], 'TURRET'], [[23, 13], 'UPGRADE'], [[4, 13], 'WALL'],
                        [[6, 13], 'WALL'], [[13, 13], 'WALL'], [[15, 13], 'WALL'], [[22, 13], 'WALL'],
                        [[24, 13], 'WALL'], [[3, 13], 'TURRET'], [[25, 13], 'TURRET'], [[3, 13], 'UPGRADE'], 
                        [[25, 13], 'UPGRADE'], [[0, 13], 'WALL'], [[1, 13], 'WALL'],
                        [[2, 13], 'WALL'], [[25, 13], 'WALL'], [[26, 13], 'WALL'], [[27, 13], 'WALL'],
                        [[0, 13], 'UPGRADE'], [[13, 13], 'UPGRADE'], [[15, 13], 'UPGRADE'],
                        [[27, 13], 'UPGRADE']]

    def build_defences(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy demolishers can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        for i in priority_queue:
            if i[1] == "WALL":
                game_state.attempt_spawn(WALL, i[0])
            elif i[1] == "TURRET":
                game_state.attempt_spawn(TURRET, i[0])
            elif i[1] == "SUPPORT":
                game_state.attempt_spawn(SUPPORT, i[0])
            elif i[1] == "UPGRADE":
                game_state.attempt_upgrade(i[0])
        
        for i in priority_queue:
            if i[1] == "WALL":
                game_state.attempt_upgrade(i[0])
    
    def build_support(self, game_state, edge):
        if edge == 1: #top_left
            game_state.attempt_spawn(SUPPORT, [8,11])
            game_state.attempt_upgrade([8,11])
            if game_state.get_resource(SP) > 12:
                game_state.attempt_spawn(SUPPORT, [11,11])
                game_state.attempt_upgrade([11,11])
        elif edge == 0: #top_right
            game_state.attempt_spawn(SUPPORT, [19,11])
            game_state.attempt_upgrade([19,11])
            if game_state.get_resource(SP) > 12:
                game_state.attempt_spawn(SUPPORT, [16,11])
                game_state.attempt_upgrade([16,11])

    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """
        for location in self.scored_on_locations:
            # Build turret one space above so that it doesn't block our own edge spawn locations
            build_location = [location[0], location[1]+1]
            game_state.attempt_spawn(TURRET, build_location)

    def stall_with_interceptors(self, game_state):
        """
        Send out interceptors at random locations to defend our base from enemy moving units.
        """
        # deploy on [[4,9], [23, 9]]
        deploy_locations = [[4,9], [23,9]]

        game_state.attempt_spawn(INTERCEPTOR, deploy_locations)
        """
        We don't have to remove the location since multiple mobile 
        units can occupy the same space.
        """

    def demolisher_line_strategy(self, game_state):
        """
        Build a line of the cheapest stationary unit so our demolisher can attack from long range.
        """
        # First let's figure out the cheapest unit
        # We could just check the game rules, but this demonstrates how to use the GameUnit class
        stationary_units = [WALL, TURRET, SUPPORT]
        cheapest_unit = WALL
        for unit in stationary_units:
            unit_class = gamelib.GameUnit(unit, game_state.config)
            if unit_class.cost[game_state.MP] < gamelib.GameUnit(cheapest_unit, game_state.config).cost[game_state.MP]:
                cheapest_unit = unit

        # Now let's build out a line of stationary units. This will prevent our demolisher from running into the enemy base.
        # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.
        for x in range(27, 5, -1):
            game_state.attempt_spawn(cheapest_unit, [x, 11])

        # Now spawn demolishers next to the line
        # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
        game_state.attempt_spawn(DEMOLISHER, [24, 10], 1000)

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy turrets that can attack each location and multiply by turret damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
            damages.append(damage)
        
        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]

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
