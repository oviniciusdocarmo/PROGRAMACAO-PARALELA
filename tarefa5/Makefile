CC      = gcc
CFLAGS  = -O2 -fopenmp -Wall -Wextra
LDFLAGS = -lm

all: primes

primes: primes.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

run: primes
	./primes

clean:
	rm -f primes

.PHONY: all run clean
