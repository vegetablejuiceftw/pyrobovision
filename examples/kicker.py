from PyMata.pymata import PyMata
from time import sleep


KICKER = 12

board = PyMata(bluetooth=False)

board.set_pin_mode(KICKER, board.OUTPUT, board.DIGITAL)

print("init with kick")
board.digital_write(KICKER, True)

sleep(0.1)
print("init recharge")
board.digital_write(KICKER, False)

sleep(2)
print("KICK")
board.digital_write(KICKER, True)


#
# while 1:
#
#     do_wat = input("do wat now?:")
#     print(repr(do_wat), bool(do_wat))
#     board.digital_write(KICKER, bool(do_wat))
#
#
#
#
#
#
# board.digital_write(KICKER, False)

