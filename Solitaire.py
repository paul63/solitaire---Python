"""
Solitaire clone.
Written by Paul Brace - March 2025
The starting point for this game is the final code in the arcade library Solitaire tutorial that can be found here:
https://api.arcade.academy/en/development/tutorials/card_game/index.html
This is © Copyright 2024, Paul Vincent Craven.
"""

import random
import time

import arcade
import pyglet

# Screen title and size
SCREEN_WIDTH = 660
SCREEN_HEIGHT = 768
SCREEN_TITLE = "Solitaire"

# Constants for sizing
CARD_SCALE = 0.6

# How big are the cards?
CARD_WIDTH = 140 * CARD_SCALE
CARD_HEIGHT = 190 * CARD_SCALE

# How big is the mat we'll place the card on?
# We will change the size of the mat as cards
# are moved so mat is not normally visible
MAT_HEIGHT = int(CARD_HEIGHT)
MAT_WIDTH = int(CARD_WIDTH)

# How much space do we leave as a gap between the mats?
# Done as a percent of the mat size.
VERTICAL_MARGIN_PERCENT = 0.10
HORIZONTAL_MARGIN_PERCENT = 0.10

# The Y of the bottom row (2 piles)
BOTTOM_Y = MAT_HEIGHT / 2 + MAT_HEIGHT * VERTICAL_MARGIN_PERCENT

# The X of where to start putting things on the left side
START_X = MAT_WIDTH / 2 + MAT_WIDTH * HORIZONTAL_MARGIN_PERCENT

# Card constants
CARD_VALUES = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
CARD_SUITS = ["Clubs", "Hearts", "Spades", "Diamonds"]

# For checking the rules om moving cards
CARD_NUMBER = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

# The Y of the top row (4 piles)
TOP_Y = SCREEN_HEIGHT - MAT_HEIGHT / 2 - MAT_HEIGHT * VERTICAL_MARGIN_PERCENT

# The Y of the middle row (7 piles)
MIDDLE_Y = TOP_Y - MAT_HEIGHT - MAT_HEIGHT * VERTICAL_MARGIN_PERCENT

# How far apart each pile goes
X_SPACING = MAT_WIDTH + MAT_WIDTH * HORIZONTAL_MARGIN_PERCENT

# If we fan out cards stacked on each other, how far apart to fan them?
CARD_VERTICAL_OFFSET = CARD_HEIGHT * CARD_SCALE * 0.3

# Constants that represent "what pile is what" for the game
PILE_COUNT = 13
BOTTOM_FACE_DOWN_PILE = 0
BOTTOM_FACE_UP_PILE = 1
PLAY_PILE_1 = 2
PLAY_PILE_2 = 3
PLAY_PILE_3 = 4
PLAY_PILE_4 = 5
PLAY_PILE_5 = 6
PLAY_PILE_6 = 7
PLAY_PILE_7 = 8
TOP_PILE_1 = 9
TOP_PILE_2 = 10
TOP_PILE_3 = 11
TOP_PILE_4 = 12

# Face down image
FACE_DOWN_IMAGE = ":resources:images/cards/cardBack_red2.png"

# For messages
DEFAULT_FONT_SIZE = 14
TEXT_LINE = 82
TEXT_COL = CARD_WIDTH * 3

# Number of winning deals to find and add to file of winning deals
NUMBER_WINNING_DEALS = 100

class Card(arcade.Sprite):
    """ Card sprite """

    def __init__(self, suit, value, scale=1):
        """ Card constructor """

        # Attributes for suit and value
        self.suit = suit
        self.value = value

        # Store number and color for rule checking
        self.number = CARD_VALUES.index(value) + 1
        if suit == "Clubs" or suit == "Spades":
            self.card_color = "Black"
        else:
            self.card_color = "Red"

        # Reset on new game to clear cards from screen
        self.moving_x = 0
        self.moving_y = 0
        self.spin = 0
        # Delay before moving card at game end
        # set based on card position
        self.delay = 0

        # Image to use for the sprite when face up
        self.image_file_name = f":resources:images/cards/card{self.suit}{self.value}.png"
        self.is_face_up = False
        super().__init__(FACE_DOWN_IMAGE, scale, hit_box_algorithm="None")

    def move(self, game_won):
        """Moves cards to clear screen at end of game"""
        if self.delay == 0:
            self.moving_x *= 0.99
            self.center_x += self.moving_x
            self.center_y += self.moving_y
            self.angle += self.spin
            if game_won and self.center_y < CARD_HEIGHT / 2:
                self.moving_y *= -1
        else:
            self.delay -= 1

    def face_down(self):
        """ Turn card face-down """
        self.texture = arcade.load_texture(FACE_DOWN_IMAGE)
        self.is_face_up = False

    def face_up(self):
        """ Turn card face-up """
        self.texture = arcade.load_texture(self.image_file_name)
        self.is_face_up = True

    @property
    def is_face_down(self):
        """ Is this card face down? """
        return not self.is_face_up

class UndoRecord():
    """Record held in undo[] which record the last move"""
    def __init__(self, from_pile, to_pile, orig_position, card):
        self.from_pile = from_pile
        self.to_pile = to_pile
        self.card = card
        self.x = orig_position[0]
        self.y = orig_position[1]

class MyGame(arcade.Window):
    """ Main application class. """

    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

        # Get display width and set screen center
        # set up the screen
        viewport = pyglet.display.get_display().get_default_screen()
        left = viewport.width // 2 - SCREEN_WIDTH // 2
        top = viewport.height // 2 - SCREEN_HEIGHT // 2
        self.set_location(left, top)

        # Sprite list with all the cards, no matter what pile they are in.
        self.card_list = None

        # List of cards we are dragging with the mouse
        self.held_cards = None

        # List of cards in last action for undo
        self.undo = []

        # Original location of cards we are dragging with the mouse in case
        # they have to go back.
        self.held_cards_original_position = None

        # Sprite list with all the mats tha cards lay on.
        self.pile_mat_list = None

        # Create a list of lists, each holds a pile of cards.
        self.piles = None

        arcade.set_background_color(arcade.color.AMAZON)

        # Text messages and option to deal 1 or 3 cards
        # Default to 1 as it is an easier mode
        self.cards_to_turn = 1
        self.mode = arcade.Text(
            "Easy (M)ode - (H)int",
            TEXT_COL,
            TEXT_LINE,
            arcade.color.WHITE,
            DEFAULT_FONT_SIZE
        )
        self.reset_message = arcade.Text(
            "(N)ew random deal - (W)inning deal",
            TEXT_COL,
            self.mode.bottom - 18,
            arcade.color.WHITE,
            DEFAULT_FONT_SIZE
        )
        self.auto_message = arcade.Text(
            "(A)uto complete hand",
            TEXT_COL,
            self.mode.bottom - 40,
            arcade.color.WHITE,
            DEFAULT_FONT_SIZE
        )
        self.undo_message = arcade.Text(
            "(U)ndo last move",
            TEXT_COL,
            self.mode.bottom - 62,
            arcade.color.WHITE,
            DEFAULT_FONT_SIZE
        )
        self.win_message = arcade.Text(
            "You Win",
            1,
            SCREEN_HEIGHT / 2,
            arcade.color.YELLOW,
            DEFAULT_FONT_SIZE * 3,
            width=SCREEN_WIDTH,
            align="center",
            bold=True
        )
        self.no_moves_message = arcade.Text(
            "No more moves",
            1,
            SCREEN_HEIGHT / 2,
            arcade.color.YELLOW,
            DEFAULT_FONT_SIZE * 3,
            width=SCREEN_WIDTH,
            align="center",
            bold=True
        )
        self.possibly_no_moves_message = arcade.Text(
            "There may be no more moves",
            1,
            SCREEN_HEIGHT / 2,
            arcade.color.YELLOW,
            DEFAULT_FONT_SIZE * 2,
            width=SCREEN_WIDTH,
            align="center",
            bold=True
        )
        # Set to true if the player completes the game
        self.game_won = False
        # A list to hold all cards at end of game
        self.all_cards = None
        # Set to true when game won or N pressed
        self.end_game = False
        # To hold current deal to be saved if it is a winning deal
        self.current_card_deal = None
        # list to hold known winning deals used if a winning deal is to be dealt
        self.winning_deals = None
        # True if player requests a winning deal
        self.deal_a_winning_deal = False
        # list of cards that could be moved
        self.hints = []
        # Length hint outlines shown on screen
        self.hint_timer = 0
        # Timer to display No more Moves
        self.no_moves_timer = 0
        # Set to true when auto complete requested
        self.auto_complete = False
        # Set to true if auto complete is just current deal.
        # If False then computer will continue
        # playing until NUMBER_WINNING_DEALS winning deals have been found and added to file
        # No instruction on screen but pressing (G)enerates winning file entries
        self.auto_current_deal_only = True
        # Number of winning deals found - used when running auto generate deals file
        self.winning_deals_found = 0
        # Number of games checked - used when generating winning deals to
        # display percentage of games that were winning deals
        self.number_games = 0
        # Used in auto complete to track if there are no more moves
        self.no_more_moves = False
        # Number of cards on last pass of face down pile used to determine that there are
        # no more moves
        self.last_pack_size = 0
        # Set to true when deck turned to check if there are any more moves
        self.no_cards_moved = False
        # To show there may be no more moves
        self.possibly_no_moves_timer = 0
        # Debug to allow mat size to be shown
        # self.show_mat_hitbox = 0
        # setup the first game
        self.setup(False)

    def get_random_movement(self):
        """Generate a random direction for card movement if game being reset"""
        result = random.randint(2, 5)
        sign = random.randint(1, 2)
        if sign == 1:
            return result
        else:
            return result * -1


    def save_cards(self, card_list):
        """Save the winning deal to a file"""
        # Only saved if we did not load a winning deal
        if not self.deal_a_winning_deal:
            with open("winning-deals-hard.txt", "a") as file:
                for card in card_list:
                    file.write(card + ",")
                file.write("\n")

    def load_a_winning_deals(self):
        """Load the list of winning deals"""
        if self.cards_to_turn == 1:
            file = "winning-deals-easy.txt"
        else:
            file = "winning-deals-hard.txt"
        self.winning_deals = []
        try:
            with open(file, "r") as file:
                while True:
                    line = file.readline()
                    if not line:
                        break
                    self.winning_deals.append(line)
                # Debug print
                print(f"{len(self.winning_deals)} winning deal(s) available")
            return True
        except:
            print("Error loading winning deals")
            return False


    def load_a_winning_deal(self):
        """Select a random winning deal from the loaded list"""
        self.load_a_winning_deals()
        if len(self.winning_deals) > 0:
            line = random.randint(0, len(self.winning_deals) - 1)
            deck = self.winning_deals[line].split(",")
            # Sprite list with all the cards, no matter what pile they are in.
            self.card_list = arcade.SpriteList()
            # Create every card
            for i in range(0, 52):
                suit = ""
                match deck[i][0]:
                    case "C":
                        suit = CARD_SUITS[0]
                    case "H":
                        suit = CARD_SUITS[1]
                    case "S":
                        suit = CARD_SUITS[2]
                    case "D":
                        suit = CARD_SUITS[3]
                if suit != "":
                    card = Card(suit, deck[i][1:], CARD_SCALE)
                    card.position = START_X, BOTTOM_Y
                    self.card_list.append(card)
            if len(self.card_list) != 52:
                print(f"Error loading cards only {len(self.card_list)} loaded")
                return False
            return True
        else:
            return False

    def clear_cards(self):
        """Set the way cards will move at the end of a game to clear screen"""
        # Move all cards to one pile
        self.end_game = True
        self.all_cards = arcade.SpriteList()
        for pile in reversed(self.piles):
            for card in pile:
                self.all_cards.append(card)
            pile = None
        if self.game_won:
            delay = 0
            x = 5
            for card in reversed(self.all_cards):
                delay += 5
                card.delay = delay
                card.moving_x = x
                card.moving_y = -5
                if delay % 65 == 0:
                    x -= 1
        else:
            for card in self.all_cards:
                card.moving_x = self.get_random_movement()
                card.moving_y = self.get_random_movement()
                card.spin = self.get_random_movement()

    def setup(self, winning_deal):
        """ Set up the game here. Call this function to restart the game.
            if winning_deal is True then a winning deal will be loaded
            if False then a random deal is generated."""

        # Number of games that have been played in this run
        self.number_games += 1

        # Reset game won flag
        self.game_won = False

        # List of cards we are dragging with the mouse
        self.held_cards = []

        # Original location of cards we are dragging with the mouse in case
        # they have to go back.
        self.held_cards_original_position = []

        # ---  Create the mats the cards go on.
        # Sprite list with all the mats tha cards lay on.
        self.pile_mat_list: arcade.SpriteList = arcade.SpriteList()

        # Create the mats for the bottom face down and face up piles
        pile = arcade.SpriteSolidColor(MAT_WIDTH, MAT_HEIGHT, arcade.csscolor.DARK_OLIVE_GREEN)
        pile.position = START_X, BOTTOM_Y
        # Color setting appears required as defaults white
        pile.color = arcade.csscolor.DARK_OLIVE_GREEN
        self.pile_mat_list.append(pile)

        pile = arcade.SpriteSolidColor(MAT_WIDTH, MAT_HEIGHT, arcade.csscolor.DARK_OLIVE_GREEN)
        pile.position = START_X + X_SPACING, BOTTOM_Y
        # Color setting appears required as defaults white
        pile.color = arcade.csscolor.DARK_OLIVE_GREEN
        self.pile_mat_list.append(pile)

        # Create the seven middle piles
        for i in range(7):
            pile = arcade.SpriteSolidColor(MAT_WIDTH, MAT_HEIGHT, arcade.csscolor.DARK_OLIVE_GREEN)
            pile.position = START_X + i * X_SPACING, MIDDLE_Y
            # PSB color setting required or background is white
            pile.color = arcade.csscolor.DARK_OLIVE_GREEN
            self.pile_mat_list.append(pile)

        # Create the top "play" piles
        for i in range(4):
            pile = arcade.SpriteSolidColor(MAT_WIDTH, MAT_HEIGHT, arcade.csscolor.DARK_OLIVE_GREEN)
            pile.position = START_X + i * X_SPACING, TOP_Y
            # PSB color setting required or background is white
            pile.color = arcade.csscolor.DARK_OLIVE_GREEN
            self.pile_mat_list.append(pile)

        # Sprite list with all the cards, no matter what pile they are in.
        self.card_list = arcade.SpriteList()


        self.current_card_deal = []
        if winning_deal and self.load_a_winning_deal():
            # A deal will have been loaded
            pass
        else:
            # Create every card
            for card_suit in CARD_SUITS:
                for card_value in CARD_VALUES:
                    card = Card(card_suit, card_value, CARD_SCALE)
                    card.position = START_X, BOTTOM_Y
                    self.card_list.append(card)

            # Shuffle cards
            for pos1 in range(len(self.card_list)):
                pos2 = random.randrange(len(self.card_list))
                self.card_list.swap(pos1, pos2)

            # Save deal in case a winning deal
            for card in self.card_list:
                self.current_card_deal.append(f"{card.suit[0]}{card.value}")

        # Create a list of lists, each holds a pile of cards.
        self.piles = [[] for _ in range(PILE_COUNT)]

        # Put all the cards in the bottom face-down pile
        for card in self.card_list:
            self.piles[BOTTOM_FACE_DOWN_PILE].append(card)

        # Pull from the face down pile into the middle piles, all face-down
        # Loop for each pile
        for pile_no in range(PLAY_PILE_1, PLAY_PILE_7 + 1):
            # Deal proper number of cards for that pile
            for j in range(pile_no - PLAY_PILE_1 + 1):
                # Pop the card off the deck we are dealing from
                card = self.piles[BOTTOM_FACE_DOWN_PILE].pop()
                # Put in the proper pile
                self.piles[pile_no].append(card)
                # Move card to same position as pile we just put it in
                card.position = self.pile_mat_list[pile_no].position
                # Put on top in draw order
                self.pull_to_top(card)

            for i, card in enumerate(self.piles[pile_no]):
                # Move cards to proper position
                card.position = self.pile_mat_list[pile_no].center_x, \
                self.pile_mat_list[pile_no].center_y - CARD_VERTICAL_OFFSET * i

            # Change mat size so it is fully covered by the card stack
            self.resize_mat(pile_no)

        # Flip up the top cards
        for i in range(PLAY_PILE_1, PLAY_PILE_7 + 1):
            self.piles[i][-1].face_up()

        # Set to true when user wins or resets game
        self.end_game = False

    def store_undo(self, source_pile, to_pile):
        """Store Undo record of cards being moved"""
        self.undo.clear()
        for index, card in enumerate(self.held_cards):
            self.undo.append(UndoRecord(source_pile, to_pile, self.held_cards_original_position[index], card))

    def on_key_press(self, symbol: int, modifiers: int):
        """ User pressed a key """
        match symbol:
            case arcade.key.U:
                # Undo last action if there is one
                # Currently only 1 level of undo
                if len(self.undo) > 0:
                    pile = self.undo[0].from_pile
                    if pile >= PLAY_PILE_1 and pile <= PLAY_PILE_7:
                        if len(self.piles[pile] > 0):
                            self.piles[pile][-1].face_down()
                    for u in self.undo:
                        self.move_card_to_new_pile(u.card, u.from_pile)
                        u.card.center_x = u.x
                        u.card.center_y = u.y
                    self.resize_mat(u.to_pile)
                    self.undo.clear()
            case arcade.key.H:
                # User requests a hint
                self.find_moves(False)
            case arcade.key.N:
                # User requests a new random deal
                self.deal_a_winning_deal = False
                self.clear_cards()
            case arcade.key.W:
                # User requests a new winning deal
                self.deal_a_winning_deal = True
                self.clear_cards()
            case arcade.key.M:
                # Change from easy to hard to easy mode
                if self.cards_to_turn == 3:
                    self.mode.text = "Easy (M)ode - (H)int"
                    self.cards_to_turn = 1
                else:
                    self.mode.text = "Hard (M)ode - (H)int"
                    self.cards_to_turn = 3
            case arcade.key.A:
                # Auto complete the current deal
                self.auto_complete = True
                self.auto_current_deal_only = True
            case arcade.key.G:
                # Generate further winning deals and add to file
                self.auto_complete = True
                self.auto_current_deal_only = False
                # There will be a game ready to play
                self.number_games = 1
                self.winning_deals_found = 0
            # case arcade.key.R:
            #     # Debug to reveal outline of mats
            #     self.show_mat_hitbox = 60

    def can_we_drop_here(self, card, pile_index):
        """ Check the rules to see if we can drop the card on the pile """
        # Check if we are dropping on a middle or top mat
        # If middle it must be of 1 lower and a different colour
        # If top it must be one higher and the same suite
        top_card = None
        if len(self.piles[pile_index]) > 0:
            top_card = self.piles[pile_index][-1]
        if TOP_PILE_1 <= pile_index <= TOP_PILE_4:
            # We are dropping on a top pile
            if top_card is None:
                # Can only drop an ace
                return card.number == 1
            else:
                # Check if one higher and the same suit
                return card.number == top_card.number + 1 and card.suit == top_card.suit
        else:
            # We are dropping on a middle pile
            if top_card is None:
                # If dropping on an empty pile then must be a King
                return card.number == 13
            else:
                # Must be one lower than the top card and a different colour
                return card.number == top_card.number - 1 and card.card_color != top_card.card_color

    def check_if_game_over(self):
        """Check if all cards on top piles and, if so, the player has won"""
        if not self.game_won:
            l = (len(self.piles[TOP_PILE_1]) + len(self.piles[TOP_PILE_2]) +
                 len(self.piles[TOP_PILE_3])) + len(self.piles[TOP_PILE_4])
            if l == 52:
                # Current deal should contain 52 cards but check just in case
                if len(self.current_card_deal) == 52:
                    # Save the winning deal
                    self.save_cards(self.current_card_deal)
                self.game_won = True
                # Set card velocity to cleat the screen
                self.clear_cards()
                self.winning_deals_found += 1
                # Debug print
                print(f"Games played {self.number_games} - Games won {self.winning_deals_found}")
                if self.winning_deals_found >= NUMBER_WINNING_DEALS:
                    # Set number found so print stats and stop auto complete
                    self.auto_complete = False
                    print(f"Games {self.number_games} of which {self.winning_deals_found} were winning deals")
                    percent = self.winning_deals_found / self.number_games * 100
                    print(f"Percent winning {percent}")

    def on_update(self, delta_time):
        """Look for next move if in auto complete and clear screen if game over"""
        # auto_current_deal_only = True just finishes the current game
        # False = repeat looking for winning deals
        if self.auto_complete:
            # Do next move
            self.find_moves(True)
            # Check if we have completed game
            self.check_if_game_over()
            if self.game_won:
                # Reset in case flag set in last game
                self.no_more_moves = False
                if not self.auto_current_deal_only:
                    # Generate next deal
                    self.setup(False)
                    return
                else:
                    # Finished auto complete
                    self.auto_complete = False

            if self.no_more_moves:
                # There are no more moves
                self.held_cards.clear()
                self.no_moves_timer = 60
                # Debug print
                # for card in self.piles[BOTTOM_FACE_DOWN_PILE]:
                #     print(f"{card.value} {card.suit}")
                if self.auto_current_deal_only:
                    self.auto_complete = False
                else:
                    self.setup(False)

        if self.end_game:
            # In end game mode to clear screen of cards
            for card in self.all_cards:
                card.move(self.game_won)
                if card.center_x < -200 or card.center_x > SCREEN_WIDTH + 200 \
                    or card.center_y < -200 or card.center_y > SCREEN_HEIGHT + 200:
                    self.all_cards.remove(card)
            if len(self.all_cards) < 1:
                # Screen cleared so set up next game
                self.setup(self.deal_a_winning_deal)

    def on_draw(self):
        """ Render the screen. """
        # Clear the screen
        self.clear()

        if self.end_game:
            # Game over so just draw the full pack in motion
            self.all_cards.draw()
            if self.game_won:
                self.win_message.draw()
        else:
            # Draw the mats the cards go on to
            self.pile_mat_list.draw()

            # Draw the cards
            self.card_list.draw()

            # Message re number of cards to turn
            self.mode.draw()

            # New game instruction
            self.reset_message.draw()

            # Auto complete instruction
            self.auto_message.draw()

            # Undo instruction
            if len(self.undo) > 0:
                self.undo_message.draw()

            # Game won message
            if self.game_won:
                self.win_message.draw()

            if self.no_moves_timer > 0:
                self.no_moves_timer -= 1
                self.no_moves_message.draw()

            if self.possibly_no_moves_timer > 0:
                self.possibly_no_moves_timer -= 1
                self.possibly_no_moves_message.draw()

            if self.hint_timer > 0:
                self.hint_timer -= 1
                for card in self.hints:
                    card.draw_hit_box(arcade.color.RED, 5)
                if self.hint_timer == 0:
                    self.hints.clear()

            # Debug
            # if self.show_mat_hitbox > 0:
            #     self.show_mat_hitbox -= 1
            #     for mat in self.pile_mat_list:
            #         mat.draw_hit_box(arcade.color.GREEN, 5)


    def find_moves(self, auto):
        """Find moves for hints and carry out the first move found if
            auto is true"""
        if auto:
            # Make sure mat size is correct
            for m in range(PLAY_PILE_1, PLAY_PILE_7 + 1):
                self.resize_mat(m)
        # Cleat the hints list
        self.hints.clear()
        # Time hint outlines will remain on screen
        self.hint_timer = 60
        # Check if we can move the visible card in each play pile to top pile
        for pile_index in range(PLAY_PILE_1, PLAY_PILE_7 + 1):
            pile = self.piles[pile_index]
            if len(pile) > 0:
                # Check if top card of middle stack can be moved to top pile
                card = pile[-1]
                for p in range(TOP_PILE_1, TOP_PILE_4 + 1):
                    if self.can_we_drop_here(card, p):
                        # If auto mode then carry out move and stop looking
                        if auto:
                            self.pull_to_top(card)
                            card.position = self.pile_mat_list[p].position
                            self.move_card_to_new_pile(card, p)
                            if len(pile) > 0:
                                pile[-1].face_up()
                            self.no_more_moves = False
                            return
                        # Not in auto mode so add to hints list
                        self.hints.append(card)
                # Check if first face up card of middle stacks can be moved to another stack
                for i, card in enumerate(pile):
                    # Find first face up card
                    if card.is_face_up:
                        if i == 0 and card.number == 13:
                            # Don't check if we can move if the face up card is a king
                            break
                        for p in range(PLAY_PILE_1, PLAY_PILE_7 + 1):
                            # Check if can be moved to another pile
                            if self.can_we_drop_here(card, p):
                                # If auto mode then carry out move and stop looking
                                if auto:
                                    self.held_cards = [card]
                                    # Put on top in drawing order
                                    self.pull_to_top(card)
                                    # Is this a stack of cards? If so, grab the other cards too
                                    #card_index = pile.index(card)
                                    for c in range(i + 1, len(pile)):
                                        card = pile[c]
                                        self.held_cards.append(card)
                                        self.pull_to_top(card)
                                    # Are there already cards in the destination pile?
                                    if len(self.piles[p]) > 0:
                                        # There are cards
                                        # Move cards to be moved to proper position
                                        top_card = self.piles[p][-1]
                                        for i, dropped_card in enumerate(self.held_cards):
                                            dropped_card.position = top_card.center_x, \
                                                top_card.center_y - CARD_VERTICAL_OFFSET * (i + 1)
                                    else:
                                        # There are no cards in the receiving pile
                                        # Move cards to proper position
                                        for i, dropped_card in enumerate(self.held_cards):
                                            dropped_card.position = self.pile_mat_list[p].center_x, \
                                                self.pile_mat_list[p].center_y - CARD_VERTICAL_OFFSET * i
                                    for card in self.held_cards:
                                        # Cards are in the right position, but we need to move them to the right list
                                        self.move_card_to_new_pile(card, p)
                                    # Turn over top card in pile moved from
                                    if len(pile) > 0:
                                        pile[-1].face_up()
                                    self.no_more_moves = False
                                    return
                                # Not in auto mode so add to hints list
                                self.hints.append(card)
                        break
        # Check if top card of face up pile can be moved
        if len(self.piles[BOTTOM_FACE_UP_PILE]) > 0:
            card = self.piles[BOTTOM_FACE_UP_PILE][-1]
            # Check if face up pile card can be moved to a top pile
            for p in range(TOP_PILE_1, TOP_PILE_4 + 1):
                if self.can_we_drop_here(card, p):
                    # If auto mode then carry out move and stop looking
                    if auto:
                        self.pull_to_top(card)
                        card.position = self.pile_mat_list[p].position
                        self.move_card_to_new_pile(card, p)
                        self.no_more_moves = False
                        return
                    # Not in auto mode so add to hints list
                    self.hints.append(card)
            # Check if face up pile card can be moved to a play pile
            for p in range(PLAY_PILE_1, PLAY_PILE_7 + 1):
                if self.can_we_drop_here(card, p):
                    # If auto mode then carry out move and stop looking
                    if auto:
                        # Put on top in drawing order
                        self.pull_to_top(card)
                        if len(self.piles[p]) > 0:
                            # There are cards in the pile being moved to
                            # Move card to proper position
                            top_card = self.piles[p][-1]
                            card.position = top_card.center_x, \
                                    top_card.center_y - CARD_VERTICAL_OFFSET
                        else:
                            # There no cards in the middle play pile?
                            # Move cards to proper position
                            card.position = self.pile_mat_list[p].center_x, \
                                self.pile_mat_list[p].center_y
                        self.move_card_to_new_pile(card, p)
                        self.no_more_moves = False
                        return
                    # Not in auto mode so add to hints list
                    self.hints.append(card)
        # If auto mode then try and turn over card from face down pile
        if auto:
            if len(self.piles[BOTTOM_FACE_DOWN_PILE]) > 0:
                # If there are cards in the face down pile turn over
                for i in range(self.cards_to_turn):
                    # If we ran out of cards, stop
                    if len(self.piles[BOTTOM_FACE_DOWN_PILE]) == 0:
                        break
                    # Get top card
                    card = self.piles[BOTTOM_FACE_DOWN_PILE][-1]
                    # Flip face up
                    card.face_up()
                    # Move card position to bottom-right face up pile
                    card.position = self.pile_mat_list[BOTTOM_FACE_UP_PILE].position
                    # Remove card from face down pile
                    self.piles[BOTTOM_FACE_DOWN_PILE].remove(card)
                    # Move card to face up list
                    self.piles[BOTTOM_FACE_UP_PILE].append(card)
                    # Put on top draw-order wise
                    self.pull_to_top(card)
                return
            else:
                if self.last_pack_size == len(self.piles[BOTTOM_FACE_UP_PILE]):
                    # We have looked through the deck once and there are no more moves
                    self.no_more_moves = True
                self.last_pack_size = len(self.piles[BOTTOM_FACE_UP_PILE])
                # No cards in face down pile
                if len(self.piles[BOTTOM_FACE_UP_PILE]) > 0:
                    # Flip the deck back over so we can restart
                    temp_list = self.piles[BOTTOM_FACE_UP_PILE].copy()
                    for card in reversed(temp_list):
                        card.face_down()
                        self.piles[BOTTOM_FACE_UP_PILE].remove(card)
                        self.piles[BOTTOM_FACE_DOWN_PILE].append(card)
                        card.position = self.pile_mat_list[BOTTOM_FACE_DOWN_PILE].position
                    return

    def on_mouse_press(self, x, y, button, key_modifiers):
        """ Called when the user presses a mouse button. """
        # Get list of cards we've clicked on
        cards = arcade.get_sprites_at_point((x, y), self.card_list)

        # Have we clicked on a card?
        if len(cards) > 0:

            # Might be a stack of cards, get the top one
            primary_card = cards[-1]
            # Figure out what pile the card is in
            pile_index = self.get_pile_for_card(primary_card)

            # Reset size of mat to no cards during move so does not display below the cards left
            top = self.pile_mat_list[pile_index].top
            self.pile_mat_list[pile_index].height = CARD_HEIGHT
            self.pile_mat_list[pile_index].top = top

            # Are we clicking on the bottom deck, to flip one or three cards?
            if pile_index == BOTTOM_FACE_DOWN_PILE:
                # Flip the cards
                # Clear undo data as can only undo last card movement action
                self.undo.clear()
                offset = 0
                # Align existing cards in face_up_pile
                count = len(self.piles[BOTTOM_FACE_UP_PILE])
                if count > 0:
                    for card in self.piles[BOTTOM_FACE_UP_PILE]:
                        card.position = self.pile_mat_list[BOTTOM_FACE_UP_PILE].position
                for i in range(self.cards_to_turn):
                    # If we ran out of cards, stop
                    if len(self.piles[BOTTOM_FACE_DOWN_PILE]) == 0:
                        break
                    # Get top card
                    card = self.piles[BOTTOM_FACE_DOWN_PILE][-1]
                    # Flip face up
                    card.face_up()
                    # Move card position to bottom-right face up pile
                    card.position = self.pile_mat_list[BOTTOM_FACE_UP_PILE].position
                    # Remove card from face down pile
                    self.piles[BOTTOM_FACE_DOWN_PILE].remove(card)
                    # Move card to face up list
                    self.piles[BOTTOM_FACE_UP_PILE].append(card)
                    # Put on top draw-order wise
                    self.pull_to_top(card)
                    card.center_x += offset
                    offset += 20
            elif primary_card.is_face_down:
                # Is the card face down? In one of those middle 7 piles? Then flip up
                # Clear undo data as can only undo last action
                self.undo.clear()

                primary_card.face_up()

                # Resize mat to height of card stack (probably not necessary)
                self.resize_mat(pile_index)
            else:
                # If face_up_pile then only take card if it is the top card
                if pile_index == BOTTOM_FACE_UP_PILE:
                    if  self.piles[pile_index].index(primary_card) == len(self.piles[pile_index]) - 1:
                        self.held_cards = [primary_card]
                        # Save the position
                        self.held_cards_original_position = [self.held_cards[0].position]
                        # Put on top in drawing order
                        self.pull_to_top(self.held_cards[0])
                else:
                    # All other cases, grab the face-up card we are clicking on
                    self.held_cards = [primary_card]
                    # Save the position
                    self.held_cards_original_position = [self.held_cards[0].position]
                    # Put on top in drawing order
                    self.pull_to_top(self.held_cards[0])

                    # Is this a stack of cards? If so, grab the other cards too
                    card_index = self.piles[pile_index].index(primary_card)
                    for i in range(card_index + 1, len(self.piles[pile_index])):
                        card = self.piles[pile_index][i]
                        self.held_cards.append(card)
                        self.held_cards_original_position.append(card.position)
                        self.pull_to_top(card)
        else:

            # Click on a mat instead of a card?
            mats = arcade.get_sprites_at_point((x, y), self.pile_mat_list)

            if len(mats) > 0:
                mat = mats[0]
                mat_index = self.pile_mat_list.index(mat)

                # Is it our turned over flip mat? and no cards on it?
                if mat_index == BOTTOM_FACE_DOWN_PILE and len(self.piles[BOTTOM_FACE_DOWN_PILE]) == 0:
                    # Check if no cards have been moved since the last flip
                    if self.no_cards_moved:
                        self.possibly_no_moves_timer = 60
                    # Flip the deck back over so we can restart
                    temp_list = self.piles[BOTTOM_FACE_UP_PILE].copy()
                    for card in reversed(temp_list):
                        card.face_down()
                        self.piles[BOTTOM_FACE_UP_PILE].remove(card)
                        self.piles[BOTTOM_FACE_DOWN_PILE].append(card)
                        card.position = self.pile_mat_list[BOTTOM_FACE_DOWN_PILE].position
                    # Flag that a card has not been moved since pack flipped
                    self.no_cards_moved = True


    # Change mat size to size and position as stack of cards
    # so mat only seen if no cards in pile
    def resize_mat(self, pile_index):
        # remember top position
        top = self.pile_mat_list[pile_index].top
        # if no cards in pile reset to card height
        if len(self.piles[pile_index]) == 0:
            self.pile_mat_list[pile_index].height = CARD_HEIGHT
        else:
            # resize height based on cards in pile
            self.pile_mat_list[pile_index].height = self.piles[pile_index][-1].bottom - \
                                                    top
        # reset top card
        self.pile_mat_list[pile_index].top = top

    def on_mouse_release(self, x: float, y: float, button: int,
                         modifiers: int):
        """ Called when the user releases a mouse button. """

        # If we don't have any cards, who cares
        if len(self.held_cards) == 0:
            return

        # Find the closest pile, in case we are in contact with more than one
        pile, distance = arcade.get_closest_sprite(self.held_cards[0], self.pile_mat_list)
        reset_position = True

        source_pile = -1

        # See if we are in contact with the closest pile
        if arcade.check_for_collision(self.held_cards[0], pile):

            # What pile is it?
            pile_index = self.pile_mat_list.index(pile)
            # What pile are we coming from
            source_pile = self.get_pile_for_card(self.held_cards[0])
            #  Is it the same pile we came from?
            if pile_index == source_pile:
                # If so, who cares. We'll just reset our position.
                pass
            # Only action if it is legal to drop the cards
            elif self.can_we_drop_here(self.held_cards[0], pile_index):
                # Is it on a middle play pile?
                if PLAY_PILE_1 <= pile_index <= PLAY_PILE_7:

                    self.store_undo(source_pile, pile_index)

                    # Are there already cards there?
                    if len(self.piles[pile_index]) > 0:
                        # Move cards to proper position
                        top_card = self.piles[pile_index][-1]
                        for i, dropped_card in enumerate(self.held_cards):
                            dropped_card.position = top_card.center_x, \
                                top_card.center_y - CARD_VERTICAL_OFFSET * (i + 1)
                    else:
                        # Are there no cards in the middle play pile?
                        for i, dropped_card in enumerate(self.held_cards):
                            # Move cards to proper position
                            dropped_card.position = pile.center_x, \
                                pile.center_y - CARD_VERTICAL_OFFSET * i

                    for card in self.held_cards:
                        # Cards are in the right position, but we need to move them to the right list
                        self.move_card_to_new_pile(card, pile_index)

                    # Success, don't reset position of cards
                    reset_position = False

                    self.resize_mat(pile_index)

                    # Flag that a card has been moved
                    self.no_cards_moved = False

                # Release on top play pile? And only one card held?
                elif TOP_PILE_1 <= pile_index <= TOP_PILE_4 and len(self.held_cards) == 1:
                    # Only action if legal to drop the cards
                    if self.can_we_drop_here(self.held_cards[0], pile_index):
                        # Move position of card to pile
                        self.held_cards[0].position = pile.position
                        # Move card to card list
                        for card in self.held_cards:
                            self.undo.clear()
                            self.store_undo(source_pile, pile_index)
                            self.move_card_to_new_pile(card, pile_index)

                        reset_position = False

                        # Flag that a card has been moved
                        self.no_cards_moved = False

                        self.check_if_game_over()

        if reset_position:
            # Where-ever we were dropped, it wasn't valid. Reset each card's position
            # to its original spot.
            for pile_index, card in enumerate(self.held_cards):
                card.position = self.held_cards_original_position[pile_index]

        # Reset size of source pile in case cards moved
        if source_pile != -1:
            self.resize_mat(source_pile)
            if len(self.piles[source_pile]) > 0:
                self.piles[source_pile][-1].face_up()

        # We are no longer holding cards
        self.held_cards = []

    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float):
        """ User moves mouse """
        # If we are holding cards, move them with the mouse
        for card in self.held_cards:
            card.center_x += dx
            card.center_y += dy

    def pull_to_top(self, card: arcade.Sprite):
        """ Pull card to top of rendering order (last to render, looks on-top) """
        # Remove, and append to the end
        self.card_list.remove(card)
        self.card_list.append(card)

    def get_pile_for_card(self, card):
        """ What pile is this card in? """
        for index, pile in enumerate(self.piles):
            if card in pile:
                return index

    def remove_card_from_pile(self, card):
        """ Remove card from whatever pile it was in. """
        for pile in self.piles:
            if card in pile:
                pile.remove(card)
                break

    def move_card_to_new_pile(self, card, pile_index):
        """ Move the card to a new pile """
        self.remove_card_from_pile(card)
        self.piles[pile_index].append(card)

def main():
    """ Main function """
    window = MyGame()
    arcade.run()


if __name__ == "__main__":
    main()

