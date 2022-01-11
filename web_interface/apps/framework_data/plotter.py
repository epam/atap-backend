import tempfile
from threading import Lock

import matplotlib.pyplot as plt
import matplotlib.ticker as pltticker

from framework import xlsdata
from wcag_information.levels_and_versions import TABLE_A, TABLE_AA, TABLE_AAA
from web_interface.apps.report.models import ConformanceLevel, Issue

lock = Lock()
wcag_2_dot_0_only_items = TABLE_A + TABLE_AA + TABLE_AAA


def make_autopct(total, state):
    def custom_autopct(pct):
        val = int(round(pct*total/100.0))
        print(f"PCT: {pct}")
        if state["slices_remaining"] > 1:
            state["slices_remaining"] -= 1
            rounded_pct = int(pct)
            state["pct_remaining"] -= rounded_pct
            return f'{val} ({rounded_pct}%)'
        else:
            return f'{val} ({state["pct_remaining"]}%)'

    return custom_autopct


def draw_pie_chart(test_results, wcag_2_dot_0_only=False):
    references, wcag_table_info, test_info, sr_versions, vpat_data, _, _ = xlsdata.load_metadata()

    WCAGs = dict()
    for wcag in wcag_table_info.keys():
        WCAGs[wcag] = {
            "PASS": 0,
            "FAIL": 0,
            "NOELEMENTS": 0
        }

    for issue_group in Issue.objects.filter(test_results=test_results):
        issue_group_wcag = issue_group.wcag
        if issue_group_wcag in WCAGs:
            WCAGs[issue_group_wcag]["FAIL"] += 1
        else:
            print(f"WCAG {issue_group_wcag} unknown")
            continue

    na, sup, dns, swe, ni = 0, 0, 0, 0, 0

    for wcag in WCAGs.keys():
        print(wcag)
        if (wcag_2_dot_0_only and (wcag in wcag_2_dot_0_only_items)) or not wcag_2_dot_0_only:
            try:
                level = ConformanceLevel.objects.get(test_results=test_results, WCAG=wcag).level
                if level == "Supports":
                    sup += 1
                    WCAGs[wcag]["support_status"] = "Supports"
                elif level == "Does Not Support":
                    dns += 1
                    WCAGs[wcag]["support_status"] = "Does not Support"
                elif level == "Supports with Exceptions":
                    swe += 1
                    WCAGs[wcag]["support_status"] = "Supports with Exceptions"
                elif level == "Not Applicable":
                    na += 1
                    WCAGs[wcag]["support_status"] = "Not Applicable"
                else:
                    ni += 1
                    WCAGs[wcag]["support_status"] = "Not Identified"

            except ConformanceLevel.DoesNotExist:
                if WCAGs[wcag]["FAIL"] == 0:
                    if WCAGs[wcag]["PASS"] == 0:
                        WCAGs[wcag]["support_status"] = "Not Applicable"
                        na += 1
                    else:
                        WCAGs[wcag]["support_status"] = "Supports"
                        sup += 1
                else:
                    if WCAGs[wcag]["PASS"] > WCAGs[wcag]["FAIL"]:
                        WCAGs[wcag]["support_status"] = "Supports with Exceptions"
                        swe += 1
                    else:
                        WCAGs[wcag]["support_status"] = "Does not Support"
                        dns += 1

    # print(f"NA:{na} SUP:{sup} DNS:{dns}, SWE:{swe}")

    data = [na, sup, dns, swe, ni]
    labels = ["Not Applicable", "Supports", "Does not Support", "Supports with Exceptions", "Not Identified"]
    colors = ["#CCCCCC", "#93C47D", "#E06666", "#FFD966", "#FFFFFF"]

    for i, label in reversed(list(enumerate(list(labels)))):
        if data[i] == 0:
            del data[i]
            del labels[i]
            del colors[i]
    with lock:
        state = {
            "pct_remaining": 100,
            "slices_remaining": len(data)
        }
        plt.clf()
        fig1, ax1 = plt.subplots()
        ax1.pie(
            data,
            labels=labels,
            wedgeprops={"edgecolor": "k", "linewidth": 1, "linestyle": "solid", "antialiased": True},
            startangle=90,
            autopct=make_autopct(sum(data), state),
            shadow=False,
            colors=colors,
            pctdistance=0.8
        )
        ax1.axis('equal')
        plt.tight_layout()
        pie_file = tempfile.NamedTemporaryFile()
        plt.savefig(pie_file, bbox_inches='tight')
        pie_file.seek(0)

    alttext = f"Pie chart with {len(data)} slices: " + ', '.join([f"{label} - {data[i]}" for i, label in enumerate(labels)])
    # print(alttext)
    return pie_file, alttext


def add_label(rect, label, v_offset=0):
    y_value = rect.get_height()
    x_value = rect.get_x() + rect.get_width() / 1
    plt.annotate(
        label,
        (x_value-0.4, y_value+v_offset),
        ha="center",
        va="bottom"
    )


def draw_bar_chart(test_results, wcag_2_dot_0_only=False):
    # references, wcag_table_info, test_info, sr_versions, _, _, _ = xlsdata.load_metadata()

    labels = ["Minor", "Major", "Critical", "Blocker"]
    data = [[0, 0], [0, 0], [0, 0], [0, 0]]
    tests_exist = False

    for issue_group in Issue.objects.filter(test_results=test_results, is_best_practice=False):
        if wcag_2_dot_0_only and any(elem in wcag_2_dot_0_only_items for elem in issue_group.wcag.split(', ')) or not wcag_2_dot_0_only:
            priority = issue_group.priority
            if priority not in labels:
                print(f"{priority} unknown")
                continue
            data[labels.index(priority)][0] += 1
            tests_exist = True
    for issue_group in Issue.objects.filter(test_results=test_results, is_best_practice=True):
        if wcag_2_dot_0_only and any(elem in wcag_2_dot_0_only_items for elem in issue_group.wcag.split(', ')) or not wcag_2_dot_0_only:
            priority = issue_group.priority
            if priority not in labels:
                print(f"{priority} unknown")
                continue
            data[labels.index(priority)][1] += 1
            tests_exist = True
    with lock:
        plt.clf()
        bar_width = 1

        x_pos_1 = [0, 5]
        x_pos_2 = [1 + x for x in x_pos_1]
        x_pos_3 = [2 + x for x in x_pos_1]
        x_pos_4 = [3 + x for x in x_pos_1]

        max_val = 0
        for datapart in data:
            for val in datapart:
                max_val = max(max_val, val)

        if not tests_exist:
            plt.ylim(0, 1)
        else:
            plt.ylim(0, max_val*1.1)

        patches_1 = plt.bar(x_pos_4, data[0], label=labels[0], color="#1c9db0").patches
        patches_2 = plt.bar(x_pos_3, data[1], label=labels[1], color="#de7826").patches
        patches_3 = plt.bar(x_pos_2, data[2], label=labels[2], color="#d45353").patches
        patches_4 = plt.bar(x_pos_1, data[3], label=labels[3], color="#000000").patches

        offset_mul = max_val/16

        for rect, val in zip(patches_1, data[0]):
            add_label(rect, "Minor", v_offset=offset_mul/2)
            if val == 0:
                continue
            add_label(rect, str(val), v_offset=-offset_mul)
        for rect, val in zip(patches_2, data[1]):
            add_label(rect, "Major", v_offset=offset_mul/2)
            if val == 0:
                continue
            add_label(rect, str(val), v_offset=-offset_mul)
        for rect, val in zip(patches_3, data[2]):
            add_label(rect, "Critical", v_offset=offset_mul/2)
            if val == 0:
                continue
            add_label(rect, str(val), v_offset=-offset_mul)
        for rect, val in zip(patches_4, data[3]):
            add_label(rect, "Blocker", v_offset=offset_mul/2)
            if val == 0:
                continue
            add_label(rect, str(val), v_offset=-offset_mul)

        WCAG_str = "WCAG 2.1" if not wcag_2_dot_0_only else "WCAG 2.0"
        plt.xticks([1.5, 6.5], [WCAG_str, "Best Practice"], color="#008296", fontsize=15)
        plt.tick_params(axis="y", colors="#008296")

        loc = pltticker.MultipleLocator(base=(int(max_val/10) + 1.0))
        plt.gca().yaxis.set_major_locator(loc)
        bottom, top = plt.ylim()
        plt.ylim(0, top)
        plt.tight_layout()

        hist_file = tempfile.NamedTemporaryFile()
        plt.savefig(hist_file, bbox_inches='tight')
        hist_file.seek(0)

    alttext = f"Bar chart with 2 groups. The first group shows the priorities of WCAG 2.1 issues: " \
              + ', '.join([f"{data[i][0]} {label}" for i, label in enumerate(labels)]) \
              + ". The second group shows the priorities of Best Practice issues: "\
              + ', '.join([f"{data[i][1]} {label}" for i, label in enumerate(labels)]) + "."

    # print(alttext)

    return hist_file, alttext
