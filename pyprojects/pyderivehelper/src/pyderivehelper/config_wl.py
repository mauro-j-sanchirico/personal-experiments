from dataclasses import dataclass


@dataclass
class SyntaxCheckResults:
    FAILED_RESULT: str = 'False'


# https://reference.wolfram.com/language/guide/DataVisualization.html


@dataclass
class PlotCommands:
    commands: list = (
        'Plot',
        'Histogram',
        'Chart',
        'Gauge',
        'Dendrogram',
        'ClusteringTree',
        'Grid',
        'Row',
        'Column',
        'Multicolumn',
        'GraphicsGrid',
        'GraphicsRow',
        'WordCloud',
        'ImageCollage',
        'ImageAssemble',
        'Scalogram',
    )
