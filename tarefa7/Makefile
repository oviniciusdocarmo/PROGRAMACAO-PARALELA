CC      = gcc
CFLAGS  = -O2 -fopenmp -Wall -Wextra
LDFLAGS =

all: files

files: files.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

run: files
	./files

clean:
	rm -f files

.PHONY: all run clean
