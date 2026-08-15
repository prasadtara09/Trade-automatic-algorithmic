def rank(signals):

    signals.sort(

        key=lambda x: x.score,

        reverse=True

    )

    return signals