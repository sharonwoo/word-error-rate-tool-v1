# Note we imported request!
from flask import Flask, render_template, request, abort
import nltk, json, os, re, warnings, operator, html, time

def _edit_dist_init(len1, len2):
    lev = []
    for i in range(len1):
        a = lev.append([0] * len2)  # initialize 2D array to zero
    for i in range(len1):
        b = lev[i][0] = i  # column 0: 0,1,2,3,4,...
    for j in range(len2):
        c = lev[0][j] = j  # row 0: 0,1,2,3,4,...
    return lev

def _edit_dist_step(lev, i, j, s1, s2, substitution_cost=1):
    c1 = s1[i - 1]   #last alphabet of the string
    c2 = s2[j - 1]   #last alphabet of the string
    a = lev[i - 1][j] + 1
    b = lev[i][j - 1] + 1
    c = lev[i - 1][j - 1] + (substitution_cost if c1 != c2 else 0)  #replacement

    # pick the cheapest
    lev[i][j] = min(a, b, c)

    return lev[i][j]

def _edit_dist_backtrace(lev):
    i, j = len(lev) - 1, len(lev[0]) - 1
    counter = []
    alignment = [(i, j)]

    while (i, j) != (0, 0):
        old_i = i
        old_j = j
        directions = [
            (i - 1, j - 1),  # substitution (diagonal)
            (i - 1, j),  # skip s1 (above)
            (i, j - 1),  # skip s2 (left)

        ]

        direction_costs = (
            (lev[i][j] if (i >= 0 and j >= 0) else float("inf"), (i, j))
            for i, j in directions
        )

        X, (i, j) = min(direction_costs, key=operator.itemgetter(0))

        if X == lev[old_i][old_j] and lev[old_i-1][old_j-1]==lev[old_i][old_j]:
            counter.append('equal')
        elif X == lev[old_i-1][old_j-1]:
            counter.append('substitution')
        elif X == lev[old_i-1][old_j]:
            counter.append('deletion')
        elif X == lev[old_i][old_j-1]:
            counter.append('insertion')
        else:
            print('error')
            continue

        alignment.append((i, j))
    return list(reversed(alignment)), counter

def edit_distance_align(s1, s2, substitution_cost=1):

    # set up a 2-D array
    len1 = len(s1)
    len2 = len(s2)
    lev = _edit_dist_init(len1 + 1, len2 + 1)

    # iterate over the array
    for i in range(len1):
        for j in range(len2):
            _edit_dist_step(
                lev,
                i + 1,
                j + 1,
                s1,
                s2,
                substitution_cost=substitution_cost,
            )

    # backtrace to find alignment
    alignment, counter = _edit_dist_backtrace(lev)
    return alignment, counter, lev[len1][len2]

def highlight_text(A,B):
    start_time = time.time()
    a = A.split(" ")
    b = B.split(" ")
    alignment, counter, edit_dist = edit_distance_align(a, b, substitution_cost=1)
    counter = list(reversed(counter))

    token_a, token_b, pointer_a, pointer_b = a, b, 0, 0
    inst, delete, subst = 0, 0, 0

    orig_text, trans_text = [], []

    div_row_start = "<div class='container-fluid'><div class='row'><div class='col-0'>"
    div_row_2 = "</div><div class='col textrow' style='border-right: 1px dotted gray;'>" # used to style divider
    div_row_3 = "</div><div class='col textrow'>" # original was used twice
    div_row_end = "</div></div></div>"

    html_combined = [div_row_start+div_row_3+"<p><u>Ground Truth</u></p>"+div_row_3+"<p><u>Machine Transcript</u></p>"+div_row_end] # start with original vs

    classname_pointer = 0

    word_counter = 0

    for index, action in enumerate(counter): # counter will always take the longest string
        if action is "equal":
            classname_pointer += 1
            try:
                orig_text.append("<div class='{}' onmouseover='highlight(this);' onmouseout='unhighlight(this);'><p class='eq'>".format('class'+str(classname_pointer))+token_a[pointer_a]+"</p></div>")
                trans_text.append("<div class='{}' onmouseover='highlight(this);' onmouseout='unhighlight(this);'><p class='eq'>".format('class'+str(classname_pointer))+token_a[pointer_a]+"</p></div>")
            except:
                abort(404)

            pointer_a += 1
            pointer_b += 1
            word_counter += 1

        elif action is "substitution":
            subst += 1
            classname_pointer += 1
            try:
                orig_text.append("<div class='{}' onmouseover='highlight(this);' onmouseout='unhighlight(this);'><p class='sub'>".format('class'+str(classname_pointer))+token_a[pointer_a]+"</p></div>")
            except:
                abort(404)
            try:
                trans_text.append("<div class='{}' onmouseover='highlight(this);' onmouseout='unhighlight(this);'><p class='sub'>".format('class'+str(classname_pointer))+token_b[pointer_b]+"</p></div>")
            except:
                abort(404)
            pointer_a += 1
            pointer_b += 1
            word_counter += 1

        elif action is "deletion":
            delete += 1
            # highlight it red
            orig_text.append("<div><p class='del'>"+token_a[pointer_a]+"</p></div>") # don't double class
            pointer_a += 1
            word_counter += 1

        # for every 20 words in the original, move on to the next row
        elif action is "insertion":
            inst += 1
            trans_text.append("<div><p class='ins'>" + token_b[pointer_b] + "</p></div>") # don't double class
            pointer_b += 1

        if word_counter == 20 or index == len(counter) - 1: # last word is reached
            word_counter = 0
            trans_text = "".join(trans_text)
            orig_text = "".join(orig_text)
            html_combined.append(div_row_start+div_row_2+"".join(orig_text)+div_row_3+"".join(trans_text)+div_row_end)
            orig_text = []
            trans_text =[]

    html_combined = ' '.join(html_combined)
    time_taken = time.time() - start_time
    return html_combined, counter, inst, delete, subst, edit_dist, len(a), round(time_taken,3)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# This page will be the page after the form
@app.route('/report')
def report():
    truth = request.args.get('truth')
    transcript = request.args.get('transcript')

    highlighted_text, counter,  insertion, deletion, substitution, edit_distance, orig_len, time_taken = highlight_text(truth, transcript)
    word_error = str(round(100*edit_distance/orig_len, 2))+'%'

    return render_template('report.html',highlighted_text=highlighted_text,
            insertion=insertion, deletion=deletion, substitution=substitution,
            word_error = word_error, time_taken = time_taken)

if __name__ == '__main__':
    app.run(debug=True)
