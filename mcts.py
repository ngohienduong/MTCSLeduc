import random
import numpy as np
from common import *
from node import *



# given a hero card and an opponent range of cards: 
# returns average percent of hero winning the hand: 0..1 
def compute_hero_p_win(hero_card, opp_range, board):
	n_win,n_lost,n_tie = 0,0,0
	v_hero = cardValue[hero_card[0]]
	v_board = cardValue[board[0][0]]
	for opp_card in opp_range:
		v_opp = cardValue[opp_card[0]]
		if v_opp == v_hero: n_tie += 1
		else:
			if v_hero == v_board: n_win += 1
			elif v_opp == v_board: n_lost += 1
			elif v_hero > v_opp: n_win += 1
			else: n_lost += 1
	n = n_win+n_lost+n_tie
	assert n > 0
	p_win = (n_win+0.5*n_tie)/n
	return p_win 


# chooses a child to explore for the node based on UCT (Upper Confidence bound applied to Trees)
# first if there are any unexplored nodes: choose one randomly
# if all nodes are explored: use UCT formula to choose the one with highest score 
def mcts_choose_child_node(node):
	n_children = len(node.nodes)
	unexplored_nodes = [i for i in range(n_children) if node.n_sim[i]==0]
	if unexplored_nodes != []:
		return random.choice(unexplored_nodes)

	# at this point: all nodes are explored, compute UCT for each and return node with max UCT 
	list_uct = []
	c = np.sqrt(2)	# a constant to guide the search in choosing the right amount between exploitation vs exploration
	for i in range(n_children):
		wi = node.ev[i]
		si = node.n_sim[i]
		sp = node.parent_n_sim
		uct = wi/si + c*np.sqrt(np.log(sp)/si)
		list_uct += [(i,uct)]
	list_uct.sort(key=lambda x:x[1], reverse=True)
	return list_uct[0][0]
	


# main MonteCarloTreeSearch function
# parameters:
#	node: a Node where we conduct the search
#	hero_card: the card hero is holding
#	opp_range: list of cards opponent can possibly hold (must not be empty)
#	player_id: player for which we want to conduct the search, either PLAYER1 or PLAYER0 constants (see common.py) 
# returns EV (expected value) for player PLAYER_ID
#
# Note: for simplicity we just use an opponent that always calls as his strategy
#   in a real simulation we would compute a strategy for each player and we would use that strategy for opponent  
def mcts_search(node, hero_card, opp_range, board, PLAYER_ID):

	# searches recursively a child node
	# if it is a chance node it averages all possible board cards
	# if it is a terminal node it returns EV won by hero
	# otherwise just call mcts_search for the child node
	def search_child_node(child_node, hero_card, opp_range, board):
		if child_node != None:
			# if it is a chance node: returns an average of all possible flops scores
			if child_node.action_str[-1:] == "|":
				assert board==[]
				list_ev = []
				for flop_card in cards:
					if flop_card == hero_card: continue
					new_opp_range = [card for card in opp_range if card != flop_card]
					if new_opp_range == []: continue	# cannot have an empty opponent list
					list_ev += [mcts_search(child_node, hero_card, new_opp_range, [flop_card], PLAYER_ID)]
				assert list_ev != []
				avg_ev = sum(list_ev)*1.0/len(list_ev)
				return avg_ev 
			else: 
				return mcts_search(child_node, hero_card, opp_range, board, PLAYER_ID)					
		else:
			# leaf node, showdown: return a weighted score
			p_win = compute_hero_p_win(hero_card, opp_range, board)
			half_pot = 0.5*node.pot							
			ev = p_win*half_pot + (1.0-p_win)*-half_pot	# when we win we win half of the pot (money opponent put into pot), when we lose we lose half of the pot (money we put into pot)
			return ev
	

	if node.player_id != PLAYER_ID:	# opp turn, choose check/call as strategy
		for action, child_node in node.nodes:
			if action == 'C':
				ev = search_child_node(child_node, hero_card, opp_range, board)
				return ev
		assert False 	# we reach this point only if no Check action is found for villain, which should not happen		   							
	else:	
		# hero's turn
		# choose either a random unexplored node or highest uct node if all nodes are explored
		child_idx = mcts_choose_child_node(node)
		
		# compute the ev of the selected child node
		action, child_node = node.nodes[child_idx]
		if action == 'F':	# Fold node, hero loses 50% of pot
			ev = -0.5*node.pot
		else:
			ev = search_child_node(child_node, hero_card, opp_range, board) 
			
		# finally update node data
		node.parent_n_sim += 1
		node.ev[child_idx] += ev
		node.n_sim[child_idx] += 1
		
		return ev
		 	

if __name__ == "__main__":
	for hero_card in ['Ah','Kh','Qh']:
		opp_range = [x for x in cards if x != hero_card]
		board = []
		
		# we re-build the game tree with each hero card
		# this is because strategy is computed for a given hero hole card
		root = node_build_tree(2, 0, "", PLAYER1)
		for _ in range(1000):
			ev = mcts_search(root, hero_card, opp_range, board, root.player_id)
		#print(ev)
		
		#print(root.nodes)
		#print(root.parent_n_sim)
		#print(root.ev)
		#print(root.n_sim)
		#print("%.2f %.2f" % (root.ev[0]/root.n_sim[0], root.ev[1]/root.n_sim[1]))
		
		print("results for hero holding %s:" % hero_card)
		for child_idx in range(len(root.nodes)):
			action, _ = root.nodes[child_idx]
			ev = root.ev[child_idx]/root.n_sim[child_idx]
			print("  action: %s ev: %.4f" % (action, ev))   
