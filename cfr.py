import random
import numpy as np
from common import *
from node import *



# given a hero card and an opponent range of cards: 
# returns average percent of hero winning the hand: 0..1 
def compute_hero_p_win(hero_card, opp_range, board):

	# special case - we got allin preflop
	# we compute a weighted sum for all boards
	if board == []:
		ev_list = [] 
		for board_card in cards:
			if board_card == hero_card: continue
			new_opp_range = [(x,freq) for x,freq in opp_range if x != board_card]
			if new_opp_range != []:
				ev_list += [compute_hero_p_win(hero_card, opp_range, [board_card])]
		assert ev_list != []
		return sum(ev_list)/len(ev_list) 
			 		

	n_win,n_lost,n_tie = 0,0,0
	v_hero = cardValue[hero_card[0]]
	v_board = cardValue[board[0][0]]
	for opp_card,freq in opp_range:
		v_opp = cardValue[opp_card[0]]
		if v_opp == v_hero: n_tie += freq
		else:
			if v_hero == v_board: n_win += freq
			elif v_opp == v_board: n_lost += freq
			elif v_hero > v_opp: n_win += freq
			else: n_lost += freq
	n = n_win+n_lost+n_tie
	assert n > 0
	p_win = (n_win+0.5*n_tie)/n
	return p_win 


# given a CFR regrets vector returns a normalized vector
# if vector has zero sum returns a vector with all actions having the same probability
def normalize_cfr_vector(v0):
	assert len(v0) > 0
	v = [max(0,x) for x in v0]	
	s = sum(v)
	if s == 0: v = [1.0/len(v) for x in v]
	else: v = [x*1.0/s for x in v] 
	return v	


# update the regrets vector:
def update_cfr_regrets_vector(hero_card, node, ev_list, opp_range):
	# compute p_freq = percent of opponent range that reaches this node
	opp_total_freq = len([x for x in cards if x != hero_card])	
	opp_local_freq = sum([freq for x,freq in opp_range])
	p_freq = opp_local_freq*1.0/opp_total_freq

	# compute weighted ev for this node
	cfr_normalized = normalize_cfr_vector(node.cfr[hero_card])
	total_ev = 0
	n_children = len(node.nodes)
	for child_idx in range(n_children): 
		total_ev += ev_list[child_idx] * cfr_normalized[child_idx] 
	
	# update cfr
	for child_idx in range(n_children):
		node.cfr[hero_card][child_idx] += (ev_list[child_idx]-total_ev) * p_freq 
		



def cfr_search(node, hero_card, opp_range, board, PLAYER_ID):
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
					new_opp_range = [(card,freq) for card,freq in opp_range if card != flop_card and freq > 0]
					if new_opp_range == []: continue	# cannot have an empty opponent list
					list_ev += [cfr_search(child_node, hero_card, new_opp_range, [flop_card], PLAYER_ID)]
				assert list_ev != []
				avg_ev = sum(list_ev)*1.0/len(list_ev)
				return avg_ev 
			else: 
				return cfr_search(child_node, hero_card, opp_range, board, PLAYER_ID)					
		else:
			# leaf node, showdown: return a weighted score
			p_win = compute_hero_p_win(hero_card, opp_range, board)
			half_pot = 0.5*node.pot							
			ev = p_win*half_pot + (1.0-p_win)*-half_pot	# when we win we win half of the pot (money opponent put into pot), when we lose we lose half of the pot (money we put into pot)
			return ev
	
	if node.player_id != PLAYER_ID:	
		# opponent turn, for each card in opp range get CFR vector normalized 
		dict_cfr_normalized = {}
		for opp_card,freq in opp_range:
			dict_cfr_normalized[opp_card] = normalize_cfr_vector(node.cfr[hero_card])
		ev_list = []
		
		# compute new range of opp cards + frequencies that go down each child subnode
		# and search each child that has opp range not zero
		for child_idx,x in enumerate(node.nodes):
			action, child_node = x
			new_opp_range = []
			for opp_card,freq in opp_range:
				new_freq = freq*dict_cfr_normalized[opp_card][child_idx]
				if new_freq > 0: new_opp_range += [(opp_card, new_freq)]
			if new_opp_range != []:
				ev = search_child_node(child_node, hero_card, new_opp_range, board)
				total_freq = sum([freq for _,freq in new_opp_range])
				ev_list += [(ev,total_freq)]
		
		# compute final ev weighted by each subchild frequency
		final_ev = sum([ev*freq for ev,freq in ev_list])/sum([freq for _,freq in ev_list])
		return final_ev
	else:	
		# hero's turn, explore all child nodes 
		n_children = len(node.nodes)
		ev_list = [0 for x in range(n_children)]
		for child_idx in range(n_children): 
			# compute the ev of the selected child node
			action, child_node = node.nodes[child_idx]
			if action == 'F':	# Fold node, hero loses 50% of pot
				ev_list[child_idx] = -0.5*node.pot
			else:
				ev_list[child_idx] = search_child_node(child_node, hero_card, opp_range, board)
		
		# update cfr regrets vector
		update_cfr_regrets_vector(hero_card, node, ev_list, opp_range)
			
		# and compute final_ev based on updated CFR vector
		cfr_normalized = normalize_cfr_vector(node.cfr[hero_card])
		ev = 0
		for child_idx in range(n_children):
			ev += ev_list[child_idx]*cfr_normalized[child_idx] 
		return ev
		 	


if __name__ == "__main__":

	# we build the game tree once
	root = node_build_tree(2, 0, "", PLAYER1)

	for iter_idx in range(50):
		print("Iteration [%d]" % iter_idx)

		for player in [PLAYER1,PLAYER2]:
			for player_card in cards:
				opp_range = [(x,1.0) for x in cards if x != player_card]	# we also send opp frequencies for each opp card
				board = []
				ev = cfr_search(root, player_card, opp_range, board, player)
		
		for hero_card in ['Ah','Kh','Qh']:
			print("results for PLAYER1 holding %s:" % hero_card)
			cfr_normalized = normalize_cfr_vector(root.cfr[hero_card])
			for child_idx in range(len(root.nodes)):
				action, _ = root.nodes[child_idx]
				print("  action: %s frequency: %.4f" % (action, cfr_normalized[child_idx]))

		for hero_card in ['Ah','Kh','Qh']:
			for node_id in [0,1]:
				node = root.nodes[node_id][1]
				print("results for PLAYER2 holding %s versus %s:" % (hero_card, node.action_str))
				cfr_normalized = normalize_cfr_vector(node.cfr[hero_card])
				for child_idx in range(len(node.nodes)):
					action, _ = node.nodes[child_idx]
					print("  action: %s frequency: %.4f" % (action, cfr_normalized[child_idx]))


		print()   
