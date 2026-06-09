CC      = gcc
CFLAGS  = -O2 -fopenmp -Wall -Wextra
LDFLAGS = -lm

all: pi_mc

pi_mc: pi_mc.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

run: pi_mc
	./pi_mc

clean:
	rm -f pi_mc

.PHONY: all run clean
