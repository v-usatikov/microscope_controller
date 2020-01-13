from multiprocessing import Process
from threading import Thread
from time import sleep


class Clock(Process):
    # my_time = 0

    def run(self):
        self.my_time = 0
        for i in range(6):
            sleep(1)
            self.my_time += 1
            print(f'Time in process:{self.my_time}')

    def run2(self):
        sleep(5)
        print('5 sec passt!')

    def get_my_time(self):
        return self.my_time



my_clock = Clock()
my_clock.start()
my_clock.run2()
print('i am starting!')

print(my_clock.get_my_time())
sleep(2)
print(my_clock.get_my_time())
sleep(3)
print(my_clock.get_my_time())

# print('hey')
# print(my_clock.my_time)
# sleep(2)
# print(my_clock.my_time)
# sleep(3)
# print(my_clock.my_time)