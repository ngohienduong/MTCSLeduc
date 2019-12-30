from common import *


# for debugging purposes we keep a list of nodes when we construct the nodes
# those variables can be ignored for now
_node_dict = {}
_node_id = [0]
def node_get_n_nodes(): return _node_id[0]
def node_get_node_dict(): return _node_dict


# Node: represents a node in the game tree
class Node:
	def __init__(self,pot,must_call,action_str,player_id):
		global _node_id,_node_dict
		self.pot = pot								# pot - money down when we reach this node
		self.must_call = must_call					# amount of money the  
		self.action_str = action_str				# action that took place until this node, see below for its encoding
		self.player_id = player_id					# id of the player acting on this node, see constants PLAYER1, PLAYER2 in common.py
		self.parent = None							# this node's parent
		self.nodes = []								# list of child nodes, for each we store an (action,child_node) tuple
													#   where action is one of 'C','R','F' for Check/Call, Bet/Raise, Fold 
													#   and child_node is a Node or None if no child nodes 
		self.id = _node_id[0]						# id of the node, unique for each node
		_node_id[0] += 1							
		_node_dict[self.id] = self
		
		# monte carlo related variables
		self.parent_n_sim = 1			# number of times simulations entered this node + 1 (cannot be 0)
		self.ev = []					# for each child node: total ev when this node was chosen
		self.n_sim = []					# for each child node: number of simulations for which this node was chosen
		
		# cfr related variables
		self.cfr = {}						# regret vector, size is equal to number of children, indexed by card 
		for c in cards: self.cfr[c] = []    # because each card at this cfr node has different CFR vector
		

# Builds recursively a game tree, returns a Node
# action_str: is the action in hand so far
#    we encode: 
#		C = check or call
#		R = bet or raise
#		F = fold
#		| = chance node, when player sees board card
def node_build_tree(pot,must_call,action_str,player_id):
	# determine which round we're dealing with
	round_id = 0
	if action_str.find("|") > 0: round_id = 1
	bet_size = 2 if round_id == 0 else 4			# bet/raise size is 2 chips first round and 4 chips second round

	# construct node
	node = Node(pot,must_call,action_str,player_id)
	
	# determine available actions for  
	actions = [ACTION_CALL_OR_CHECK]
	if not action_str.endswith("RR"):
		actions += [ACTION_RAISE]
	if must_call > 0: actions += [ACTION_FOLD]
	
	for action in actions:
		if action == ACTION_FOLD:
			node.nodes += [('F',None)]
		elif action == ACTION_CALL_OR_CHECK:
			if round_id==1 and action_str[-1:] in ["C","R"]:
				node.nodes += [('C',None)]
			else:										# we have further action!
				if round_id < 1 and (must_call > 0 or (must_call <= 0 and action_str[-1:]=='C')) and len(action_str) >= 1:	# see if calling ends current stage
					n = node_build_tree(pot+2*must_call,0,action_str+"C|",PLAYER1)
				else:
					assert must_call==0
					n = node_build_tree(pot,0,action_str+"C",1-player_id)
				n.parent = node
				node.nodes += [('C',n)]
		else:
			ch = 'R'
			new_pot = pot+2*bet_size
			new_must_call = bet_size
			n = node_build_tree(new_pot,new_must_call,action_str+ch,1-player_id)
			n.parent = node
			node.nodes += [(ch,n)]
	
	node.ev = [0] * len(actions)
	node.n_sim = [0] * len(actions)			
	for c in cards:
		node.cfr[c] = [0] * len(actions)			
	return node


if __name__ == "__main__":
	root = node_build_tree(2, 0, "", PLAYER1)
	
	for node_id in _node_dict:
		node = _node_dict[node_id]
		print("[%s]" % node.action_str, node.pot, node.must_call, node.player_id)
		