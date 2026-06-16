CC      = gcc
CFLAGS  = -O2 -fopenmp -Wall -Wextra
LDFLAGS = -lm

all: pi_cache

pi_cache: pi_cache.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

run: pi_cache
	./pi_cache

clean:
	rm -f pi_cache

.PHONY: all run clean
