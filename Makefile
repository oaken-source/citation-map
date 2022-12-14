
all: timeline.svg graph.svg

clean:
	$(RM) timeline.gz timeline.svg graph.gz graph.svg

CSV = Exported\ Items.csv

.PHONY: all clean

timeline.svg: timeline.gz
	dot $< -Tsvg >$@

graph.svg: graph.gz
	fdp $< -Tsvg >$@

graph.gz: $(CSV) analyze_papers.py
	python analyze_papers.py "$<" >$@

timeline.gz: $(CSV) analyze_papers.py
	python analyze_papers.py "$<" -t >$@

