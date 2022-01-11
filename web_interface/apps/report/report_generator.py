import tempfile
from web_interface.apps.framework_data import plotter
from framework.report import docx_report


def generate_report(task, delta_starting_task):
    wcag = '21'
    test_results = task.test_results
    wcag_20_only = False
    if wcag == '20':
        wcag_20_only = True
    # if len(AuditReportParams.objects.filter(test_results=task.test_results)) == 1:
    #     report_params = AuditReportParams.objects.get(test_results=task.test_results)
    # else:
    #     report_params = AuditReportParams.objects.create(
    #         name='default',
    #         creator=user,
    #         test_results=task.test_results
    #     )
    # else:
    #     report_params = AuditReportParams.objects.create(
    #         name='test',
    #         creator_id=1,
    #         test_results=Task.objects.all().order_by('-id')[0].test_results
    #     )
    #     task = report_params.test_results.task

    conformance_graph, conformance_graph_alt = plotter.draw_pie_chart(
        test_results,
        wcag_2_dot_0_only=wcag_20_only
    )
    prioritization_graph, prioritization_graph_alt = plotter.draw_bar_chart(
        test_results,
        wcag_2_dot_0_only=wcag_20_only
    )
    report_file = tempfile.NamedTemporaryFile()
    docx_report.AuditReport(
        test_results=test_results,
        delta_starting_test_results=delta_starting_task.test_results if delta_starting_task is not None else None,
        graphs={
            'conformance': conformance_graph,
            'conformance_alt': conformance_graph_alt,
            'prioritization': prioritization_graph,
            'prioritization_alt': prioritization_graph_alt
        },
        wcag_2_dot_0_only=wcag_20_only
    ).create_report(report_file.name)
    conformance_graph.close()
    prioritization_graph.close()
    report_file.seek(0)
    return report_file
