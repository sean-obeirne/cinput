import cinput as i
import time
import logging

logging.basicConfig(filename='debug.log', level=logging.DEBUG, filemode='w', format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# cw = i.init()
cw = i.CommandWindow()

loglevel = 0

while input:
    input = cw.get_input("hello!", default="hey default!", input_type="text")
    # cw.help(["add", "append", "delete", "edit", "quit"])
    # time.sleep(1)
    # cw.help([("h", "help")])
    # selection = cw.make_selection("Idk its a message", ["buster brown", "billy goat jr", "wenie hut general"], default="1")
    # log.info(f"selection : {selection}")

    # log.info(f"input: {input}")
    # log.info(f"selection: {selection}")

    # time.sleep(3)
