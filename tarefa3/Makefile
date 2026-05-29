CC     = gcc
CFLAGS = -Wall -std=c11 -O2
SRC    = pi.c

all: pi

pi: $(SRC)
	$(CC) $(CFLAGS) -o $@ $< -lm

run: all
	./pi

clean:
	rm -f pi
