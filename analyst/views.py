from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.contrib import messages
from .models import Dataset
from .services import FileService, ProfilingService, KPIService, ChartingService, AIService
import json

def get_active_dataset():
    dataset_id = None
    # In a real app, we'd use session or user.
    # For this MVP, we'll take the latest uploaded dataset.
    dataset = Dataset.objects.last()
    return dataset

def upload_view(request):
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            messages.error(request, "Please upload a file.")
            return redirect('upload')

        # Save dataset
        dataset = Dataset.objects.create(file=uploaded_file)

        # Process data
        df = FileService.load_dataframe(dataset.file.path)
        if df is None:
            messages.error(request, "Unable to read this file. Please upload a valid CSV or Excel file.")
            return redirect('upload')

        df = FileService.normalize_columns(df)
        profile, num_cols = ProfilingService.generate_profile(df)
        kpis = KPIService.calculate_kpis(df)

        # Cache results in DB
        dataset.profile_data = profile
        dataset.kpi_data = kpis
        dataset.save()

        messages.success(request, "File uploaded and analyzed successfully!")
        return redirect('dashboard')

    return render(request, 'analyst/upload.html')

def dashboard_view(request):
    dataset = get_active_dataset()
    if not dataset:
        return redirect('upload')

    df = FileService.load_dataframe(dataset.file.path)
    df = FileService.normalize_columns(df)

    # Use cached profile and KPIs
    profile = dataset.profile_data
    kpis = dataset.kpi_data

    # Generate Plotly JSONs
    charts = {}
    chart_ids = [
        "generic_cat", "cgpa_dept", "placement_dept", "salary_dept",
        "cgpa_dist", "attendance_dist", "cgpa_attendance_scatter",
        "salary_dist", "correlation"
    ]

    chart_service = ChartingService()
    for cid in chart_ids:
        json_fig = chart_service.get_chart_json(df, cid)
        if json_fig:
            charts[cid] = json_fig

    return render(request, 'analyst/dashboard.html', {
        'dataset': dataset,
        'profile': profile,
        'kpis': kpis,
        'charts': charts,
    })

def insights_view(request):
    dataset = get_active_dataset()
    if not dataset:
        return redirect('upload')

    df = FileService.load_dataframe(dataset.file.path)
    df = FileService.normalize_columns(df)

    # Re-calculate profile to get num_cols for context
    profile, num_cols = ProfilingService.generate_profile(df)

    ai_service = AIService()
    context = ai_service.build_analysis_context(df, profile, num_cols)
    insights = ai_service.get_insights(context)

    return render(request, 'analyst/insights.html', {
        'dataset': dataset,
        'insights': insights,
    })

def ask_view(request):
    if request.method == 'POST':
        question = request.POST.get('question')
        dataset = get_active_dataset()
        if not dataset:
            return JsonResponse({'error': 'No dataset available'}, status=400)

        df = FileService.load_dataframe(dataset.file.path)
        df = FileService.normalize_columns(df)

        ai_service = AIService()
        answer = ai_service.ask_ai(df, question)

        return JsonResponse({'answer': answer})

    return render(request, 'analyst/ask.html')
