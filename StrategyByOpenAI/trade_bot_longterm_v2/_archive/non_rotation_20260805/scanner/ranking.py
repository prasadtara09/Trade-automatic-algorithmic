def rank_signals(signals):

    return sorted(

        signals,

        key=lambda s: (

            s.score,

            s.atr

        ),

        reverse=True

    )