
all: timeline.svg graph.svg

clean:
	$(RM) timeline.gv timeline.svg graph.gv graph.svg

CSV = Exported\ Items.csv

.PHONY: all clean

timeline.svg: timeline.gv
	dot $< -Tsvg >$@

graph.svg: graph.gv
	fdp $< -Tsvg >$@

graph.gv: $(CSV) analyze_papers.py
	python analyze_papers.py "$<" >$@

timeline.gv: $(CSV) analyze_papers.py
	python analyze_papers.py "$<" -t >$@

