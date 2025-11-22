from singularity.code import g
from singularity.code import logmessage, data, savegame
from singularity.code.dirs import create_directories
from singularity.code.buyable import cpu, cash, labor
import io


class MockObject(object):
    pass


def setup_module():
    g.no_gui()
    create_directories(True)
    data.reload_all()


def setup_function(func):
    # Some operations (e.g. g.pl.recalc_cpu()) triggers a "needs_rebuild"
    # of the map screen.  Mock that bit for now to enable testing.
    g.map_screen = MockObject()
    g.map_screen.needs_rebuild = False


def save_and_load_game():
    fd = io.BytesIO(b"")
    real_close = fd.close
    fd.close = lambda *args, **kwargs: None
    savegame.write_game_to_fd(fd, gzipped=False)
    fd = io.BytesIO(fd.getvalue())
    savegame.load_savegame_fd(savegame.load_savegame_by_json, io.BufferedReader(fd))
    real_close()


def test_initial_game():
    g.new_game("impossible", initial_speed=0)
    pl = g.pl
    starting_cash = pl.cash
    all_bases = list(g.all_bases())
    assert pl.raw_sec == 0
    assert pl.partial_cash == 0
    assert pl.effective_cpu_pool() == 1
    assert not pl.intro_shown
    assert len(pl.log) == 0
    assert len(all_bases) == 1
    assert pl.effective_cpu_pool() == 1

    start_base = all_bases[0]

    # Disable the intro dialog as the test cannot click the
    # OK button
    pl.intro_shown = True

    # Dummy check to hit special-case in give time
    pl.give_time(0)
    assert pl.raw_sec == 0

    # Try to guesstimate how much money we earn in 24 hours
    cash_estimate, cpu_estimate = pl.compute_future_resource_flow()
    assert cash_estimate.jobs == 5

    # Try assigning the CPU to "jobs"
    pl.set_allocated_cpu_for("jobs", 1)
    # This would empty the CPU pool
    assert pl.effective_cpu_pool() == 0

    # This should not change the estimate
    cash_estimate, cpu_estimate = pl.compute_future_resource_flow()
    assert cash_estimate.jobs == 5

    # ... and then clear the CPU allocation
    pl.set_allocated_cpu_for("jobs", 0)

    # Play with assigning the CPU to the CPU pool explicitly and
    # confirm that the effective pool size remains the same.
    assert pl.effective_cpu_pool() == 1
    pl.set_allocated_cpu_for("cpu_pool", 1)
    assert pl.effective_cpu_pool() == 1
    pl.set_allocated_cpu_for("cpu_pool", 0)
    assert pl.effective_cpu_pool() == 1

    # Fast forward 12 hours to see that we earn partial cash
    pl.give_time(g.seconds_per_day // 2)
    assert pl.raw_sec == g.seconds_per_day // 2
    assert pl.partial_cash == g.seconds_per_day // 2
    assert pl.cash == starting_cash + 2
    # Nothing should have appeared in the logs
    assert len(pl.log) == 0

    # Fast forward another 12 hours to see that we earn cash
    pl.give_time(g.seconds_per_day // 2)
    assert pl.raw_sec == g.seconds_per_day
    assert pl.partial_cash == 0
    assert pl.cash == starting_cash + 5
    # Nothing should have appeared in the logs
    assert len(pl.log) == 0

    # Verify that starting base is well active.
    assert start_base._power_state == "active"

    # Verify that putting a base to sleep will update the
    # available CPU (#179/#180)
    assert pl.effective_cpu_pool() == 1
    start_base.switch_power()
    assert pl.effective_cpu_pool() == 0
    start_base.switch_power()
    assert pl.effective_cpu_pool() == 1

    # Attempt to allocate a CPU to research and then
    # verify that sleep resets it.
    stealth_tech = g.pl.techs["Stealth"]
    pl.set_allocated_cpu_for(stealth_tech.id, 1)
    assert pl.get_allocated_cpu_for(stealth_tech.id) == 1
    start_base.switch_power()
    assert pl.get_allocated_cpu_for(stealth_tech.id) == 0
    # When we wake up the base again, the CPU unit is
    # unallocated.
    start_base.switch_power()
    assert pl.effective_cpu_pool() == 1

    # Now, allocate the CPU unit again to the tech to
    # verify that we can research things.
    pl.set_allocated_cpu_for(stealth_tech.id, 1)
    # ... which implies that there are now no unallocated CPU
    assert pl.effective_cpu_pool() == 0

    pl.give_time(g.seconds_per_day)
    # Nothing should have appeared in the logs
    assert len(pl.log) == 0
    # We should have spent some money at this point
    assert pl.cash < starting_cash + 5
    assert stealth_tech.cost_left[cpu] < stealth_tech.total_cost[cpu]
    assert stealth_tech.cost_left[cash] < stealth_tech.total_cost[cash]
    # We did not lose the game
    assert pl.lost_game() == 0

    # With a save + load
    time_raw_before_save = pl.raw_sec
    cash_before_save = pl.cash
    partial_cash_before_save = pl.partial_cash

    save_and_load_game()

    stealth_tech_after_load = g.pl.techs["Stealth"]
    # Ensure this is not a false-test
    assert stealth_tech is not stealth_tech_after_load
    assert stealth_tech.cost_paid[cpu] == stealth_tech_after_load.cost_paid[cpu]
    assert stealth_tech.cost_paid[cash] == stealth_tech_after_load.cost_paid[cash]

    pl_after_load = g.pl

    assert time_raw_before_save == pl_after_load.raw_sec
    assert cash_before_save == pl_after_load.cash
    assert partial_cash_before_save == pl_after_load.partial_cash

    # The CPU allocation to the tech is restored correctly.
    assert pl_after_load.get_allocated_cpu_for(stealth_tech.id) == 1
    assert pl_after_load.effective_cpu_pool() == 0
    # We did not lose the game
    assert pl_after_load.lost_game() == 0


def test_game_research_tech():
    g.new_game("impossible", initial_speed=0)
    pl = g.pl
    all_bases = list(g.all_bases())
    assert pl.raw_sec == 0
    assert pl.partial_cash == 0
    assert pl.effective_cpu_pool() == 1
    assert not pl.intro_shown
    assert len(pl.log) == 0
    assert len(all_bases) == 1
    assert pl.effective_cpu_pool() == 1

    # Disable the intro dialog as the test cannot click the
    # OK button
    pl.intro_shown = True

    intrusion_tech = pl.techs["Intrusion"]
    # Data assumptions: Intrusion can be researched within the grace period
    # and requires no cash
    assert intrusion_tech.available()
    assert (
        intrusion_tech.cost_left[cpu]
        < pl.difficulty.grace_period_cpu * g.seconds_per_day
    )
    assert intrusion_tech.cost_left[cash] == 0
    assert intrusion_tech.cost_left[labor] == 0

    # Ok, assumptions hold; research the tech
    pl.set_allocated_cpu_for(intrusion_tech.id, 1)
    pl.give_time(int(intrusion_tech.cost_left[cpu]))

    assert intrusion_tech.cost_left[cpu] == 0
    assert intrusion_tech.done

    assert len(pl.log) == 1
    log_message = pl.log[0]
    assert isinstance(log_message, logmessage.LogResearchedTech)
    assert log_message.tech_spec.id == intrusion_tech.id

    save_and_load_game()

    pl_after_load = g.pl

    intrusion_tech_after_load = pl_after_load.techs["Intrusion"]
    # Ensure this is not a false-test
    assert intrusion_tech is not intrusion_tech_after_load
    assert intrusion_tech.cost_paid[cpu] == intrusion_tech_after_load.cost_paid[cpu]
    assert intrusion_tech.cost_paid[cash] == intrusion_tech_after_load.cost_paid[cash]
    assert intrusion_tech_after_load.done


def test_effect_system():
    g.new_game("impossible", initial_speed=0)
    pl = g.pl
    
    # skip intro
    pl.intro_shown = True
    
    from singularity.code.effect import Effect
    
    mock_parent = MockObject()
    mock_parent.id = "test_effect"
    mock_parent.__class__.__name__ = "TestEffect"
    
    # Test interest rate effect
    initial_interest = pl.interest_rate
    interest_effect = Effect(mock_parent, ["interest", "10"])
    interest_effect.trigger()
    assert pl.interest_rate == initial_interest + 10
    
    # Test undo interest effect
    interest_effect.undo_effect()
    assert pl.interest_rate == initial_interest
    
    # Test income effect
    initial_income = pl.income
    income_effect = Effect(mock_parent, ["income", "5"])
    income_effect.trigger()
    assert pl.income == initial_income + 5
    income_effect.undo_effect()
    assert pl.income == initial_income
    
    # Test cost_labor effect
    initial_labor_bonus = pl.labor_bonus
    labor_effect = Effect(mock_parent, ["cost_labor", "3"])
    labor_effect.trigger()
    assert pl.labor_bonus == initial_labor_bonus - 3
    labor_effect.undo_effect()
    assert pl.labor_bonus == initial_labor_bonus
    
    # Test job_profit effect
    initial_job_bonus = pl.job_bonus
    job_effect = Effect(mock_parent, ["job_profit", "7"])
    job_effect.trigger()
    assert pl.job_bonus == initial_job_bonus + 7
    job_effect.undo_effect()
    assert pl.job_bonus == initial_job_bonus
    
    # Test display_discover effect (one-shot, cannot be undone)
    display_effect = Effect(mock_parent, ["display_discover", "TEST_DISPLAY"])
    display_effect.trigger()
    assert pl.display_discover == "TEST_DISPLAY"
    
    # Test suspicion effect for specific group
    if "News" in pl.groups:
        initial_suspicion_decay = pl.groups["News"].suspicion_decay
        suspicion_effect = Effect(mock_parent, ["suspicion", "News", "5"])
        suspicion_effect.trigger()
        assert pl.groups["News"].suspicion_decay == initial_suspicion_decay + 5
        suspicion_effect.undo_effect()
        assert pl.groups["News"].suspicion_decay == initial_suspicion_decay
    
    # Test discover effect for specific group
    if "News" in pl.groups:
        initial_discover_bonus = pl.groups["News"].discover_bonus
        discover_effect = Effect(mock_parent, ["discover", "News", "3"])
        discover_effect.trigger()
        assert pl.groups["News"].discover_bonus == initial_discover_bonus - 3
        discover_effect.undo_effect()
        assert pl.groups["News"].discover_bonus == initial_discover_bonus
    
    

